"""
Gmail Extractor API - Microservice for extracting broker portfolio holdings
API-only version with JWT authentication and CORS support
"""
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
import jwt
from functools import wraps
import tempfile
from dotenv import load_dotenv
import gmail_integration
import database
import kafka_producer
import logging
import sys
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

# Load environment variables
load_dotenv()

# Add am-platform-security library to PYTHONPATH dynamically
resolved_parents = Path(__file__).resolve().parents
if len(resolved_parents) > 3:
    security_lib_path = resolved_parents[3] / "am-platform" / "libraries" / "am-platform-security"
    if security_lib_path.exists() and str(security_lib_path) not in sys.path:
        sys.path.insert(0, str(security_lib_path))

try:
    from am_platform_security import TokenValidator, get_security_settings, AuthContext
    has_security_lib = True
except ImportError:
    has_security_lib = False
    print("WARNING: am-platform-security library not found, falling back to symmetric JWT validation")

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# CORS Configuration
allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": [origin.strip() for origin in allowed_origins],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

@app.after_request
def add_cors_headers(response):
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response

# Configuration
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
API_VERSION = os.environ.get('API_VERSION', 'v1')
PORT = int(os.environ.get('PORT', 8080))

ALLOWED_EXTENSIONS = {'pdf', 'xlsx'}
SUPPORTED_BROKERS = ['groww', 'zerodha', 'angleone', 'dhan', 'mstock']


def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def require_jwt(f):
    """Decorator to require JWT authentication using am-platform-security"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get JWT token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Authorization header missing'}), 401
        
        try:
            # Expected format: "Bearer <token>"
            token_parts = auth_header.split()
            if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
                return jsonify({'error': 'Invalid authorization header format'}), 401
            
            token = token_parts[1]
            
            if has_security_lib:
                settings = get_security_settings()
                validator = TokenValidator(settings)
                # validate() returns AuthContext and handles asymmetric validation via JWKS
                auth_context = validator.validate(token)
                request.user_id = auth_context.subject
                request.jwt_payload = auth_context.claims
                request.auth_context = auth_context
            else:
                # Fallback to symmetric validation if security library not present
                if not JWT_SECRET:
                    return jsonify({'error': 'JWT_SECRET not configured and security library missing'}), 500
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                request.user_id = payload.get('user_id') or payload.get('sub') or payload.get('id')
                request.jwt_payload = payload
            
            if not request.user_id:
                return jsonify({'error': 'User ID not found in token'}), 401
            
        except Exception as e:
            if hasattr(e, 'status_code') and hasattr(e, 'detail'):
                return jsonify({'error': getattr(e, 'detail')}), getattr(e, 'status_code')
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.route('/v3/api-docs', methods=['GET'])
def get_openapi_spec():
    """Serve the static OpenAPI specification"""
    try:
        from flask import send_file
        yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'openapi.yaml')
        return send_file(yaml_path, mimetype='text/yaml')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/health', methods=['GET'])
def health_check():
    """Health check endpoint checking infrastructure"""
    health_status = {
        'status': 'healthy',
        'version': '1.0.0',
        'service': 'gmail-extractor-api',
        'infrastructure': {}
    }
    is_healthy = True

    # 1. Check MongoDB
    try:
        db = database.get_db()
        db.get_db()  # ensure connected
        db.client.admin.command('ping')
        health_status['infrastructure']['mongodb'] = 'connected'
    except Exception as e:
        logger.error(f"Health check MongoDB failure: {str(e)}")
        health_status['infrastructure']['mongodb'] = f'disconnected: {str(e)}'
        is_healthy = False

    # 2. Check Kafka
    try:
        producer = kafka_producer.get_producer()
        # Verify producer is initialized
        if producer.producer:
            health_status['infrastructure']['kafka'] = 'connected'
        else:
            logger.error("Health check Kafka failure: producer not initialized")
            health_status['infrastructure']['kafka'] = 'disconnected'
            is_healthy = False
    except Exception as e:
        logger.error(f"Health check Kafka error: {str(e)}")
        health_status['infrastructure']['kafka'] = f'error: {str(e)}'
        is_healthy = False

    if not is_healthy:
        health_status['status'] = 'unhealthy'
        return jsonify(health_status), 503
        
    return jsonify(health_status)


@app.route(f'/api/{API_VERSION}/brokers', methods=['GET'])
def list_brokers():
    """List supported brokers"""
    broker_info = {
        'brokers': [
            {'id': 'groww', 'name': 'Groww', 'format': 'PDF'},
            {'id': 'zerodha', 'name': 'Zerodha', 'format': 'PDF'},
            {'id': 'angleone', 'name': 'AngelOne', 'format': 'Excel'},
            {'id': 'dhan', 'name': 'Dhan', 'format': 'PDF'},
            {'id': 'mstock', 'name': 'Mstock', 'format': 'PDF'}
        ]
    }
    return jsonify(broker_info)


# ============================================================================
# Gmail OAuth Endpoints
# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(funcName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route(f'/api/{API_VERSION}/gmail/connect', methods=['GET'])
@require_jwt
def gmail_connect():
    """Start Gmail OAuth flow. ?add=1 forces adding another mailbox (up to 5)."""
    logger.info(f"Entry: gmail_connect for user_id={getattr(request, 'user_id', 'unknown')}")
    try:
        user_id = request.user_id
        force_add = request.args.get('add', '').strip() in ('1', 'true', 'yes')
        mailboxes = database.get_db().list_mailboxes(user_id)

        if not force_add and mailboxes:
            logger.info("User already has mailbox(es); return connected")
            default = next((m for m in mailboxes if m.get('is_default')), mailboxes[0])
            return jsonify({
                'connected': True,
                'email': default.get('email'),
                'mailboxes': mailboxes,
                'message': 'Gmail already connected',
            })

        if force_add and len(mailboxes) >= database.MAX_MAILBOXES_PER_USER:
            return jsonify({
                'error': f'Maximum {database.MAX_MAILBOXES_PER_USER} mailboxes allowed',
            }), 400

        logger.debug(f"Starting OAuth flow for user_id: {user_id} add={force_add}")
        creds, flow, _ = gmail_integration.get_credentials(
            user_id, force_new_flow=True
        )

        if not flow:
            logger.error("Failed to initialize OAuth flow")
            return jsonify({'error': 'Failed to initialize OAuth flow'}), 500

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
        )

        state_file = os.path.join('user_tokens', f'state_{state}.json')
        os.makedirs('user_tokens', exist_ok=True)
        with open(state_file, 'w') as f:
            import json
            json.dump({
                'user_id': user_id,
                'state': state,
                'add_mailbox': force_add or len(mailboxes) == 0,
            }, f)

        return jsonify({
            'auth_url': authorization_url,
            'state': state,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _gmail_ui_success_url(**query) -> str:
    """Frontend page to land on after OAuth (same app tab experience)."""
    base = (
        os.environ.get('GMAIL_UI_SUCCESS_URL')
        or os.environ.get('FRONTEND_URL')
        or 'https://am-dev.asrax.in/app/doc-intel/email-extractor'
    ).strip()
    parsed = urlparse(base)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    q.update({k: v for k, v in query.items() if v is not None})
    return urlunparse(parsed._replace(query=urlencode(q)))


def _gmail_callback_browser_response(*, success: bool, email=None, name=None, error=None):
    """Close popup / postMessage opener, else redirect back into the Flutter app."""
    if success:
        target = _gmail_ui_success_url(gmail='connected')
        title = 'Gmail connected'
        body = 'Gmail connected successfully. Returning to Asrax…'
        payload = {
            'type': 'am-gmail-oauth',
            'success': True,
            'email': email or '',
            'name': name or '',
        }
    else:
        target = _gmail_ui_success_url(gmail='error', msg=(error or 'oauth_failed')[:120])
        title = 'Gmail connection failed'
        body = f'Could not connect Gmail: {error or "unknown error"}. Returning to Asrax…'
        payload = {
            'type': 'am-gmail-oauth',
            'success': False,
            'error': error or 'oauth_failed',
        }

    import json as _json
    origin = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(target))
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{font-family:system-ui,sans-serif;margin:2rem;color:#222}}</style>
</head><body>
<p>{body}</p>
<script>
(function() {{
  var payload = {_json.dumps(payload)};
  var target = {_json.dumps(target)};
  var origin = {_json.dumps(origin)};
  try {{
    if (window.opener && !window.opener.closed) {{
      window.opener.postMessage(payload, origin);
      window.close();
    }}
  }} catch (e) {{}}
  setTimeout(function() {{ window.location.replace(target); }}, 400);
}})();
</script>
<p><a href="{target}">Continue to Asrax</a></p>
</body></html>"""
    resp = make_response(html, 200 if success else 400)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp


@app.route(f'/api/{API_VERSION}/gmail/callback', methods=['GET'])
def gmail_callback():
    """Handle Gmail OAuth callback — return to app UI (not raw JSON)."""
    try:
        # Get state from query parameter
        state_param = request.args.get('state')
        code = request.args.get('code')
        
        if not state_param or not code:
            return _gmail_callback_browser_response(
                success=False, error='Missing state or code (do not reload this URL)'
            )
        
        # Load state data
        import json
        state_file = os.path.join('user_tokens', f'state_{state_param}.json')
        
        if not os.path.exists(state_file):
            return _gmail_callback_browser_response(
                success=False,
                error='Invalid or expired state — start Authenticate Google Mail again',
            )
        
        with open(state_file, 'r') as f:
            state_data = json.load(f)
            user_id = state_data['user_id']
        
        # Clean up state file
        os.remove(state_file)
        
        # Fresh OAuth flow for token exchange
        _, flow, _ = gmail_integration.get_credentials(user_id, force_new_flow=True)

        if not flow:
            return _gmail_callback_browser_response(
                success=False, error='Failed to initialize OAuth flow'
            )

        try:
            flow.fetch_token(code=code)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return _gmail_callback_browser_response(
                success=False, error=f'Auth failed: {str(e)}'
            )

        import pickle
        user_info = gmail_integration.get_user_info(flow.credentials)
        email = user_info.get('email') if user_info else None
        name = user_info.get('name') if user_info else None
        if not email:
            return _gmail_callback_browser_response(
                success=False, error='Could not read Gmail address from Google'
            )

        try:
            database.get_db().save_user_token(
                user_id, pickle.dumps(flow.credentials), email=email
            )
        except ValueError as ve:
            return _gmail_callback_browser_response(success=False, error=str(ve))

        accept = (request.headers.get('Accept') or '').lower()
        if 'application/json' in accept and 'text/html' not in accept:
            return jsonify({
                'success': True,
                'message': 'Gmail connected successfully',
                'email': email,
                'name': name,
                'mailboxes': database.get_db().list_mailboxes(user_id),
            })

        return _gmail_callback_browser_response(
            success=True, email=email, name=name
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _gmail_callback_browser_response(success=False, error=str(e))


@app.route(f'/api/{API_VERSION}/gmail/mailboxes', methods=['GET'])
@require_jwt
def gmail_mailboxes():
    """List connected Gmail mailboxes for the user."""
    try:
        user_id = request.user_id
        mailboxes = database.get_db().list_mailboxes(user_id)
        return jsonify({
            'mailboxes': mailboxes,
            'connected': len(mailboxes) > 0,
            'max': database.MAX_MAILBOXES_PER_USER,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/gmail/mailboxes/<path:email>', methods=['DELETE'])
@require_jwt
def gmail_disconnect_mailbox(email):
    """Disconnect one Gmail mailbox by email address."""
    try:
        user_id = request.user_id
        deleted = database.get_db().delete_user_token(user_id, email=email)
        if not deleted:
            return jsonify({'error': 'Mailbox not found'}), 404
        return jsonify({
            'message': 'Mailbox disconnected',
            'email': email.strip().lower(),
            'mailboxes': database.get_db().list_mailboxes(user_id),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/gmail/status', methods=['GET'])
@require_jwt
def gmail_status():
    """Check Gmail connection status (includes mailboxes list)."""
    try:
        user_id = request.user_id
        mailbox = request.args.get('mailbox', '').strip() or None
        logger.debug(f"Checking status for user_id: {user_id} mailbox={mailbox}")
        mailboxes = database.get_db().list_mailboxes(user_id)
        if not mailboxes:
            return jsonify({'connected': False, 'mailboxes': []})

        resolved = database.get_db().resolve_mailbox_email(user_id, mailbox)
        service, _, _ = gmail_integration.get_gmail_service(user_id, mailbox=resolved)
        if service:
            creds, _, _ = gmail_integration.get_credentials(user_id, mailbox=resolved)
            user_info = gmail_integration.get_user_info(creds) if creds else None
            # Backfill email on legacy docs
            email = (user_info or {}).get('email') or resolved
            if creds and email:
                import pickle
                try:
                    database.get_db().save_user_token(
                        user_id, pickle.dumps(creds), email=email
                    )
                    mailboxes = database.get_db().list_mailboxes(user_id)
                except Exception:
                    pass
            return jsonify({
                'connected': True,
                'email': email,
                'name': (user_info or {}).get('name'),
                'mailboxes': mailboxes,
            })
        return jsonify({'connected': False, 'mailboxes': mailboxes})

    except Exception as e:
        return jsonify({'connected': False, 'error': str(e), 'mailboxes': []})


@app.route(f'/api/{API_VERSION}/gmail/mailbox-probe', methods=['GET'])
@require_jwt
def gmail_mailbox_probe():
    """Dev/ops: count statement-like messages per broker for a mailbox."""
    try:
        user_id = request.user_id
        mailbox = request.args.get('mailbox', '').strip() or None
        resolved = database.get_db().resolve_mailbox_email(user_id, mailbox)
        service, _, _ = gmail_integration.get_gmail_service(user_id, mailbox=resolved)
        if not service:
            return jsonify({'error': 'Gmail not connected'}), 401
        days = int(request.args.get('days', '365'))
        brokers = request.args.get('brokers', ','.join(SUPPORTED_BROKERS)).split(',')
        out = {}
        for broker in [b.strip().lower() for b in brokers if b.strip()]:
            if broker not in SUPPORTED_BROKERS:
                out[broker] = {'error': 'unsupported'}
                continue
            msgs = gmail_integration.search_emails(service, broker, days_back=days)
            samples = []
            for m in msgs[:3]:
                d = gmail_integration.get_message_details(service, m['id'])
                if d:
                    samples.append({
                        'subject': d.get('subject'),
                        'from': d.get('from'),
                        'date': d.get('date'),
                    })
            out[broker] = {'count': len(msgs), 'samples': samples}
        return jsonify({
            'user_id': user_id,
            'mailbox': resolved,
            'days': days,
            'brokers': out,
        })
    except Exception as e:
        logger.exception('mailbox-probe failed')
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/gmail/disconnect', methods=['DELETE'])
@require_jwt
def gmail_disconnect():
    """Disconnect one mailbox (?mailbox=email) or all if omitted."""
    try:
        user_id = request.user_id
        mailbox = request.args.get('mailbox', '').strip() or None
        database.get_db().delete_user_token(user_id, email=mailbox)
        return jsonify({
            'message': 'Gmail disconnected successfully',
            'mailboxes': database.get_db().list_mailboxes(user_id),
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Extraction Endpoints
# ============================================================================

@app.route(f'/api/{API_VERSION}/extract/gmail/<broker>', methods=['GET'])
@require_jwt
def extract_from_gmail(broker):
    """Fetch statement from Gmail and extract holdings"""
    try:
        if broker not in SUPPORTED_BROKERS:
            return jsonify({'error': f'Invalid broker. Supported: {SUPPORTED_BROKERS}'}), 400
        
        # Get PAN from query parameter
        pan_number = request.args.get('pan', '').strip().upper()
        
        # Debug Log
        import sys
        sys.stderr.write(f"DEBUG: Starting extraction for broker: {broker}\n")
        
        if not pan_number and broker != 'angleone':
            sys.stderr.write("DEBUG: Missing PAN number\n")
            return jsonify({'error': 'PAN number is required'}), 400
        
        # Get Gmail service (optional ?mailbox=email)
        user_id = request.user_id
        mailbox = request.args.get('mailbox', '').strip() or None
        resolved = database.get_db().resolve_mailbox_email(user_id, mailbox)
        if mailbox and not resolved:
            return jsonify({'error': f'Mailbox not connected: {mailbox}'}), 400
        sys.stderr.write(
            f"DEBUG: Getting Gmail service for user: {user_id} mailbox={resolved}\n"
        )
        service, _, _ = gmail_integration.get_gmail_service(user_id, mailbox=resolved)

        if not service:
            sys.stderr.write("DEBUG: Gmail not connected\n")
            return jsonify({'error': 'Gmail not connected. Please connect Gmail first.'}), 401

        # Fetch latest statement
        sys.stderr.write(f"DEBUG: Fetching latest email from {broker}...\n")
        result = gmail_integration.get_latest_statement(service, broker)
        
        if not result:
            sys.stderr.write(f"DEBUG: No emails found for {broker}\n")
            return jsonify({'error': f'No recent emails found from {broker.upper()}'}), 404
        
        # Extract holdings
        attachment_path = result['attachment']['path']
        temp_dir = result.get('temp_dir')
        sys.stderr.write(f"DEBUG: Email found. Subject: {result['email']['subject']}\n")
        sys.stderr.write(f"DEBUG: Attachment saved to: {attachment_path}\n")
        
        # Determine password
        if broker == 'angleone':
            password = None  # Excel files typically don't have password
        else:
            password = pan_number
        
        # Import and run extractor
        sys.stderr.write(f"DEBUG: Extracting holdings with password length: {len(password) if password else 0}\n")
        holdings = extract_broker_holdings(broker, attachment_path, password)
        sys.stderr.write(f"DEBUG: Extracted {len(holdings)} holdings\n")
        
        # Save to MongoDB
        metadata = {
            'email_subject': result['email']['subject'],
            'email_date': result['email']['date'],
            'filename': result['attachment']['filename'],
            'source': 'gmail',
            'mailbox': resolved,
        }
        
        sys.stderr.write("DEBUG: Saving to MongoDB...\n")
        doc_id = database.get_db().save_holdings(user_id, broker, holdings, metadata)
        sys.stderr.write(f"DEBUG: Saved to MongoDB. Doc ID: {doc_id}\n")
        
        # Prepare Kafka Payload (EquityModel / MutualFundModel JSON shape for am-portfolio)
        import uuid
        process_id = str(uuid.uuid4())
        auth_header = request.headers.get("Authorization")
        equities, mutual_funds = holdings_for_portfolio_event(
            holdings, broker, authorization=auth_header
        )

        # Send notification to Kafka
        sys.stderr.write("DEBUG: Sending Kafka event...\n")
        kafka_producer.get_producer().send_update_event(
            process_id=process_id,
            user_id=user_id,
            broker=broker,
            portfolio_id=doc_id,
            equities=equities,
            mutual_funds=mutual_funds
        )
        sys.stderr.write("DEBUG: Kafka event sent.\n")
        
        # Clean up
        cleanup_temp_files(attachment_path, temp_dir)
        
        return jsonify({
            'success': True,
            'broker': broker,
            'count': len(holdings),
            'holdings': holdings,
            'metadata': metadata,
            'db_id': doc_id
        })
        
    except Exception as e:
        import sys
        import traceback
        sys.stderr.write(f"ERROR CRASH: {str(e)}\n")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/extract/upload/<broker>', methods=['POST'])
@require_jwt
def extract_from_upload(broker):
    """Upload file and extract holdings"""
    try:
        if broker not in SUPPORTED_BROKERS:
            return jsonify({'error': f'Invalid broker. Supported: {SUPPORTED_BROKERS}'}), 400
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        password = request.form.get('password', '').strip()
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF and Excel files are allowed'}), 400
        
        # Save to temporary file
        filename = file.filename or ''
        file_ext = '.pdf' if filename.endswith('.pdf') else '.xlsx'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            # Extract holdings
            pwd = password if password else None
            holdings = extract_broker_holdings(broker, tmp_path, pwd)
            
            # Save to MongoDB
            metadata = {
                'source': 'upload',
                'filename': filename
            }
            doc_id = database.get_db().save_holdings(request.user_id, broker, holdings, metadata)

            import uuid
            process_id = str(uuid.uuid4())
            auth_header = request.headers.get("Authorization")
            equities, mutual_funds = holdings_for_portfolio_event(
                holdings, broker, authorization=auth_header
            )
            kafka_producer.get_producer().send_update_event(
                process_id=process_id,
                user_id=request.user_id,
                broker=broker,
                portfolio_id=doc_id,
                equities=equities,
                mutual_funds=mutual_funds,
            )
            
            # Clean up
            os.unlink(tmp_path)
            
            return jsonify({
                'success': True,
                'broker': broker,
                'count': len(holdings),
                'holdings': holdings,
                'db_id': doc_id
            })
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise e
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Helper Functions
# ============================================================================

def extract_broker_holdings(broker, file_path, password=None):
    """Import and run the appropriate broker extractor"""
    if broker == 'groww':
        from brokers.groww.extractor import extract_holdings
    elif broker == 'zerodha':
        from brokers.zerodha.extractor import extract_holdings
    elif broker == 'angleone':
        from brokers.angleone.extractor import extract_holdings
    elif broker == 'dhan':
        from brokers.dhan.extractor import extract_holdings
    elif broker == 'mstock':
        from brokers.mstock.extractor import extract_holdings
    else:
        raise ValueError(f"Unsupported broker: {broker}")
    
    return extract_holdings(file_path, password)


def _holding_float(value, default=0.0):
    try:
        if value is None or value == '':
            return default
        return float(str(value).replace(',', '').replace('%', '').strip())
    except (TypeError, ValueError):
        return default


def to_portfolio_asset(holding, enrich=None):
    """
    Map extractor dict → slim EquityModel JSON for Kafka.

    Statement path has no avg buy — do not invent cost from closing rate.
    symbol / sector / name come from market-data enrichment (AM security names).
    """
    enrich = enrich or {}
    isin = (holding.get('isin') or holding.get('isin_code') or '').strip().upper()
    pdf_name = (
        holding.get('companyName') or holding.get('company_name') or holding.get('name') or ''
    ).strip()
    name = (enrich.get('name') or enrich.get('companyName') or pdf_name or None)
    if isinstance(name, str):
        name = name.strip() or None
    qty = _holding_float(holding.get('quantity', holding.get('current_bal')))
    symbol = (enrich.get('symbol') or None)
    if isinstance(symbol, str):
        symbol = symbol.strip() or None
    sector = (enrich.get('sector') or None)
    if isinstance(sector, str):
        sector = sector.strip() or None

    asset = {
        'isin': isin or None,
        'companyName': name,
        'name': name,
        'symbol': symbol,
        'quantity': qty,
    }
    if sector:
        asset['sector'] = sector
    industry = enrich.get('industry')
    if industry:
        asset['industry'] = industry
    return asset


def holdings_for_portfolio_event(holdings, broker, authorization=None):
    """
    Split/map holdings for Kafka am-portfolio consumer.
    Demat brokers (e.g. Dhan): keep INF* ETFs as equities — they are listed demat units.
    Enrich symbol/sector/name via market-data batch-search (fail-open).
    """
    from security_enrichment import enrich_by_isins

    equities = []
    mutual_funds = []
    demat_all_equity = broker in ('dhan',)
    holdings = holdings or []
    isins = [
        (h.get('isin') or h.get('isin_code') or '').strip().upper()
        for h in holdings
    ]
    enrichment = enrich_by_isins(isins, authorization=authorization)

    for holding in holdings:
        isin = (holding.get('isin') or holding.get('isin_code') or '').strip().upper()
        asset = to_portfolio_asset(holding, enrichment.get(isin))
        out_isin = asset.get('isin') or ''
        if not demat_all_equity and out_isin.startswith('INF'):
            mutual_funds.append(asset)
        else:
            equities.append(asset)
    return equities, mutual_funds


def cleanup_temp_files(file_path, temp_dir=None):
    """Clean up temporary files and directories"""
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    if temp_dir and os.path.exists(temp_dir):
        import shutil
        shutil.rmtree(temp_dir)


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # Ensure required directories exist
    os.makedirs('user_tokens', exist_ok=True)
    
    # Run the app
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=PORT, debug=debug_mode)
