"""
Gmail Extractor API - Microservice for extracting broker portfolio holdings
API-only version with JWT authentication and CORS support
"""
from flask import Flask, request, jsonify
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
                # Fallback to OIDC JWKS or symmetric validation if security library not present
                jwks_url = os.environ.get('OIDC_JWKS_URL')
                if jwks_url:
                    jwks_client = jwt.PyJWKClient(jwks_url)
                    signing_key = jwks_client.get_signing_key_from_jwt(token)
                    issuer = os.environ.get('OIDC_ISSUER')
                    
                    decode_kwargs = {
                        "algorithms": ["RS256"],
                        "options": {"verify_aud": False, "verify_iss": False}
                    }
                        
                    payload = jwt.decode(token, signing_key.key, **decode_kwargs)
                    request.user_id = payload.get('user_id') or payload.get('sub') or payload.get('id')
                    request.jwt_payload = payload
                elif JWT_SECRET:
                    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                    request.user_id = payload.get('user_id') or payload.get('sub') or payload.get('id')
                    request.jwt_payload = payload
                else:
                    return jsonify({'error': 'OIDC_JWKS_URL or JWT_SECRET not configured and security library missing'}), 500
            
            if not request.user_id:
                return jsonify({'error': 'User ID not found in token'}), 401
            
        except Exception as e:
            import traceback
            print(f"JWT Validation Error: {type(e).__name__}: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            
            if hasattr(e, 'status_code') and hasattr(e, 'detail'):
                return jsonify({'error': getattr(e, 'detail')}), getattr(e, 'status_code')
            return jsonify({'error': f'Invalid token: {type(e).__name__} - {str(e)}'}), 401
        
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
        # Ping the database
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
    """Start Gmail OAuth flow"""
    logger.info(f"Entry: gmail_connect for user_id={getattr(request, 'user_id', 'unknown')}")
    try:
        user_id = request.user_id
        logger.debug(f"Getting credentials for user_id: {user_id}")
        creds, flow, _ = gmail_integration.get_credentials(user_id)
        
        if creds:
            logger.info("User already authenticated")
            user_info = gmail_integration.get_user_info(creds)
            return jsonify({
                'connected': True,
                'email': user_info.get('email') if user_info else None,
                'message': 'Gmail already connected'
            })
        
        if not flow:
            logger.error("Failed to initialize OAuth flow")
            return jsonify({'error': 'Failed to initialize OAuth flow'}), 500
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent'
        )
        
        # Store state for verification during callback
        # We still use a temporary file for STATE because callback needs to verify state
        # State is short-lived and doesn't contain sensitive credentials, just a nonce
        state_file = os.path.join('user_tokens', f'state_{state}.json')
        os.makedirs('user_tokens', exist_ok=True)
        with open(state_file, 'w') as f:
            import json
            json.dump({
                'user_id': user_id,
                'state': state
            }, f)
        
        return jsonify({
            'auth_url': authorization_url,
            'state': state
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/gmail/callback', methods=['GET'])
def gmail_callback():
    """Handle Gmail OAuth callback"""
    try:
        # Get state from query parameter
        state_param = request.args.get('state')
        code = request.args.get('code')
        
        if not state_param or not code:
            return jsonify({'error': 'Missing state or code parameter'}), 400
        
        # Load state data
        import json
        state_file = os.path.join('user_tokens', f'state_{state_param}.json')
        
        if not os.path.exists(state_file):
            return jsonify({'error': 'Invalid or expired state'}), 400
        
        with open(state_file, 'r') as f:
            state_data = json.load(f)
            user_id = state_data['user_id']
        
        # Clean up state file
        os.remove(state_file)
        
        # Get credentials and exchange code for token
        creds, flow, _ = gmail_integration.get_credentials(user_id)
        
        if not flow:
            return jsonify({'error': 'Failed to initialize OAuth flow'}), 500
        
        # Fetch token
        try:
            # We must pass the same redirect_uri to fetch_token if it's not handled by the flow
            flow.fetch_token(code=code)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Auth failed: {str(e)}'}), 401
        
        # Save credentials to Database
        import pickle
        database.get_db().save_user_token(user_id, pickle.dumps(flow.credentials))
        
        # Get user info
        user_info = gmail_integration.get_user_info(flow.credentials)
        
        # Return success with user info
        return jsonify({
            'success': True,
            'message': 'Gmail connected successfully',
            'email': user_info.get('email') if user_info else None,
            'name': user_info.get('name') if user_info else None
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/gmail/status', methods=['GET'])
@require_jwt
def gmail_status():
    """Check Gmail connection status"""
    try:
        user_id = request.user_id
        logger.debug(f"Checking status for user_id: {user_id}")
        service, _, _ = gmail_integration.get_gmail_service(user_id)
        
        if service:
            # Get user info
            creds, _, _ = gmail_integration.get_credentials(user_id)
            user_info = gmail_integration.get_user_info(creds) if creds else None
            
            return jsonify({
                'connected': True,
                'email': user_info.get('email') if user_info else None,
                'name': user_info.get('name') if user_info else None
            })
        else:
            return jsonify({'connected': False})
            
    except Exception as e:
        return jsonify({'connected': False, 'error': str(e)})


@app.route(f'/api/{API_VERSION}/gmail/disconnect', methods=['DELETE'])
@require_jwt
def gmail_disconnect():
    """Disconnect Gmail account"""
    try:
        user_id = request.user_id
        database.get_db().delete_user_token(user_id)
        return jsonify({'message': 'Gmail disconnected successfully'})
            
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
        
        # Get Gmail service
        user_id = request.user_id
        sys.stderr.write(f"DEBUG: Getting Gmail service for user: {user_id}\n")
        service, _, _ = gmail_integration.get_gmail_service(user_id)
        
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
            'source': 'gmail'
        }
        
        sys.stderr.write("DEBUG: Saving to MongoDB...\n")
        doc_id = database.get_db().save_holdings(user_id, broker, holdings, metadata)
        sys.stderr.write(f"DEBUG: Saved to MongoDB. Doc ID: {doc_id}\n")
        
        # Prepare Kafka Payload
        import uuid
        process_id = str(uuid.uuid4())
        
        equities = []
        mutual_funds = []
        
        for holding in holdings:
            # Simple ISIN check: INF usually Mutual Fund, INE usually Equity
            isin = holding.get('isin_code', '')
            if isin.startswith('INF'):
                mutual_funds.append(holding)
            else:
                equities.append(holding)
        
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
            
            # Send notification to Kafka
            kafka_producer.get_producer().send_update_event(
                user_id=request.user_id,
                status="SUCCESS",
                db_id=doc_id,
                broker=broker
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
