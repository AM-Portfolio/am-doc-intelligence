from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import os
import json
from werkzeug.utils import secure_filename
import tempfile
import gmail_integration

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Initialize Flask app

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Session configuration for OAuth flow
app.config['SESSION_COOKIE_SAMESITE'] = None  # More permissive for OAuth redirects
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session lasts 1 hour

ALLOWED_EXTENSIONS = {'pdf', 'xlsx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit(
        '.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    return redirect('/')


@app.route('/')
def index():
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    return render_template('index.html',
                           user_name=user_name,
                           user_email=user_email)


@app.route('/groww')
def groww():
    user_name = session.get('user_name')
    return render_template('groww/index.html',
                           broker='groww',
                           user_name=user_name)


@app.route('/zerodha')
def zerodha():
    user_name = session.get('user_name')
    return render_template('zerodha/index.html',
                           broker='zerodha',
                           user_name=user_name)


@app.route('/angleone')
def angleone():
    user_name = session.get('user_name')
    return render_template('angleone/index.html',
                           broker='angleone',
                           user_name=user_name)


@app.route('/dhan')
def dhan():
    user_name = session.get('user_name')
    return render_template('dhan/index.html',
                           broker='dhan',
                           user_name=user_name)


@app.route('/mstock')
def mstock():
    user_name = session.get('user_name')
    return render_template('mstock/index.html',
                           broker='mstock',
                           user_name=user_name)


@app.route('/gmail')
def gmail():
    user_name = session.get('user_name')
    return render_template('gmail/index.html', user_name=user_name)


@app.route('/gmail/authorize')
def gmail_authorize():
    """Start Gmail OAuth flow"""
    try:
        # Make session permanent to persist during OAuth flow
        session.permanent = True
        
        # Generate a unique session ID if not exists
        if 'session_id' not in session:
            import uuid
            session['session_id'] = str(uuid.uuid4())

        user_id = session['session_id']
        creds, flow, token_file = gmail_integration.get_credentials(user_id)

        if creds:
            # Already authenticated
            return redirect('/gmail')

        if not flow:
            return jsonify({'error': 'Failed to initialize OAuth flow'}), 500

        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline', include_granted_scopes='true')

        # Store state and token file in session AND in a temporary file
        # (workaround for cookie blocking)
        session['state'] = state
        session['token_file'] = token_file
        
        # Also store in a file as backup
        import json
        state_file = os.path.join('user_tokens', f'state_{state}.json')
        os.makedirs('user_tokens', exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump({
                'user_id': user_id,
                'token_file': token_file,
                'state': state
            }, f)

        return redirect(authorization_url)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/gmail/callback')
def gmail_callback():
    """Handle OAuth callback"""
    try:
        # Debug: Print session contents
        print(f"=== CALLBACK DEBUG ===")
        print(f"Session keys: {list(session.keys())}")
        print(f"Session ID in session: {session.get('session_id')}")
        print(f"State in session: {session.get('state')}")
        
        # Try to get from session first
        state = session.get('state')
        user_id = session.get('session_id')
        token_file = session.get('token_file')

        # If session is empty, try to load from file (workaround for cookie blocking)
        if not user_id:
            # Get state from URL parameter
            state_param = request.args.get('state')
            if state_param:
                import json
                state_file = os.path.join('user_tokens', f'state_{state_param}.json')
                if os.path.exists(state_file):
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                        user_id = state_data['user_id']
                        token_file = state_data['token_file']
                        state = state_data['state']
                        print(f"Loaded state from file: user_id={user_id}")
                    # Clean up the state file
                    os.remove(state_file)
        
        if not user_id:
            print(f"ERROR: No user_id in session or file!")
            return jsonify({'error': 'Session expired'}), 401

        creds, flow, _ = gmail_integration.get_credentials(user_id)

        if not flow:
            return redirect('/gmail')

        # Fetch token
        flow.fetch_token(authorization_response=request.url)

        # Save credentials for this specific user
        import pickle
        if token_file:
            with open(token_file, 'wb') as token:
                pickle.dump(flow.credentials, token)

        # Get user info and store in session
        user_info = gmail_integration.get_user_info(flow.credentials)
        if user_info:
            session['user_name'] = user_info.get('name', 'User')
            session['user_email'] = user_info.get('email', '')

        return redirect('/gmail')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/gmail/status')
def gmail_status():
    """Check Gmail authentication status"""
    try:
        # Get user ID from session
        user_id = session.get('session_id')

        service, flow, _ = gmail_integration.get_gmail_service(user_id)
        if service:
            # If authenticated but no user name in session, fetch it now
            if not session.get('user_name'):
                creds, _, _ = gmail_integration.get_credentials(user_id)
                if creds:
                    user_info = gmail_integration.get_user_info(creds)
                    if user_info:
                        session['user_name'] = user_info.get('name', 'User')
                        session['user_email'] = user_info.get('email', '')

            return jsonify({
                'authenticated': True,
                'user_name': session.get('user_name'),
                'user_email': session.get('user_email')
            })
        else:
            return jsonify({'authenticated': False})
    except Exception as e:
        return jsonify({'authenticated': False})


@app.route('/gmail/fetch/<broker>')
def gmail_fetch(broker):
    """Fetch latest statement from Gmail for a broker"""
    try:
        if broker not in ['groww', 'zerodha', 'angleone', 'dhan', 'mstock']:
            return jsonify({'error': 'Invalid broker'}), 400

        # Get PAN from query parameter
        pan_number = request.args.get('pan', '').strip().upper()

        if not pan_number:
            return jsonify({'error': 'PAN number is required'}), 400

        # Get Gmail service for this user
        user_id = session.get('session_id')
        service, flow, _ = gmail_integration.get_gmail_service(user_id)

        if not service:
            return jsonify({'error': 'Not authenticated with Gmail'}), 401

        # Fetch latest statement
        result = gmail_integration.get_latest_statement(service, broker)

        if not result:
            return jsonify(
                {'error':
                 f'No recent emails found from {broker.upper()}'}), 404

        # Extract holdings from the downloaded file
        attachment_path = result['attachment']['path']
        temp_dir = result.get('temp_dir')

        # Determine password - use PAN for most brokers, except Dhan which might use a different format
        # Users can override by providing their specific password
        if broker == 'dhan':
            # Dhan might use a different PAN format or password
            password = pan_number
        elif broker == 'angleone':
            password = ''  # AngleOne Excel files typically don't have password
        else:
            # Groww, Zerodha, MSTOCK use PAN as password
            password = pan_number

        # Import appropriate extractor and extract holdings
        if broker == 'groww':
            from brokers.groww.extractor import extract_holdings
            holdings = extract_holdings(attachment_path,
                                        password if password else None)
        elif broker == 'zerodha':
            from brokers.zerodha.extractor import extract_holdings
            holdings = extract_holdings(attachment_path,
                                        password if password else None)
        elif broker == 'angleone':
            from brokers.angleone.extractor import extract_holdings
            holdings = extract_holdings(attachment_path,
                                        password if password else None)
        elif broker == 'dhan':
            from brokers.dhan.extractor import extract_holdings
            holdings = extract_holdings(attachment_path,
                                        password if password else None)
        elif broker == 'mstock':
            from brokers.mstock.extractor import extract_holdings
            holdings = extract_holdings(attachment_path,
                                        password if password else None)
        else:
            return jsonify({'error': 'Unsupported broker'}), 400

        # Clean up temp file and directory
        if os.path.exists(attachment_path):
            os.remove(attachment_path)
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)

        return jsonify({
            'broker': broker,
            'count': len(holdings),
            'holdings': holdings,
            'email_subject': result['email']['subject'],
            'email_date': result['email']['date'],
            'filename': result['attachment']['filename']
        })

    except Exception as e:
        print(f"Error in gmail_fetch: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/extract/<broker>', methods=['POST'])
def extract(broker):
    try:
        if broker not in ['groww', 'zerodha', 'angleone', 'dhan', 'mstock']:
            return jsonify({'error': 'Invalid broker'}), 400

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        password = request.form.get('password', '').strip()

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error':
                            'Only PDF and Excel files are allowed'}), 400

        # Save to temporary file with appropriate extension
        filename = file.filename or ''
        file_ext = '.pdf' if filename.endswith('.pdf') else '.xlsx'
        with tempfile.NamedTemporaryFile(delete=False,
                                         suffix=file_ext) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name

        try:
            # Import the appropriate extractor
            extract_holdings = None
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

            if extract_holdings is None:
                raise Exception(f"Unsupported broker: {broker}")

            # Extract holdings
            pwd = password if password else None
            holdings = extract_holdings(tmp_path, pwd)

            # Clean up temp file
            os.unlink(tmp_path)

            return jsonify({
                'success': True,
                'holdings': holdings,
                'count': len(holdings),
                'broker': broker
            })

        except Exception as e:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            import traceback
            error_msg = str(e) if str(e) else "Unknown extraction error"
            print(f"Extraction error for {broker}: {error_msg}")
            print(traceback.format_exc())
            return jsonify({'error': f'Extraction failed: {error_msg}'}), 500

    except Exception as e:
        import traceback
        error_msg = str(e) if str(e) else "Unknown server error"
        print(f"Server error: {error_msg}")
        print(traceback.format_exc())
        return jsonify({'error': error_msg}), 500


@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        holdings = data.get('holdings', [])
        broker = data.get('broker', 'holdings')

        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w',
                                         delete=False,
                                         suffix='.json') as tmp_file:
            json.dump(holdings, tmp_file, indent=2)
            tmp_path = tmp_file.name

        return send_file(tmp_path,
                         mimetype='application/json',
                         as_attachment=True,
                         download_name=f'{broker}_portfolio_holdings.json')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
