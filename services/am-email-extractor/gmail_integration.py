import os
import base64
import pickle
import tempfile
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Allow OAuth over HTTP when behind a reverse proxy (like Replit)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

# Broker email patterns
BROKER_PATTERNS = {
    'zerodha': {
        'from': 'no-reply-transaction-with-holding-statement@reportsmailer.zerodha.net',
        'subject': 'Monthly Demat Transaction with Holding Statement for',
        'file_pattern': '.pdf'
    },
    'groww': {
        'from': 'noreply@groww.in',
        'subject': 'Transaction and Holding Statement',
        'file_pattern': '.pdf'
    },
    'dhan': {
        'from': 'statements@dhan.co',
        'subject': 'Demat Transaction and Holding Statement for the Month ending',
        'file_pattern': '.pdf'
    },
    'mstock': {
        'from': 'no-reply@mstock.com',
        'subject': 'TRANSACTION STATEMENT',
        'file_pattern': '.pdf'
    },
    'angleone': {
        'from': 'noreply@angelone.in',
        'subject': 'Holdings',
        'file_pattern': '.xlsx'
    }
}

def get_credentials(user_id=None):
    """Get Gmail API credentials for a specific user"""
    creds = None
    import database
    
    # Use database for token storage if user_id is provided
    if user_id:
        try:
            token_data = database.get_db().get_user_token(user_id)
            if token_data:
                creds = pickle.loads(token_data)
        except Exception as e:
            print(f"Error loading token from DB: {e}")
            creds = None
    else:
        # Fallback to local file for backward compatibility or no-user checks
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
    
    # If credentials are invalid or don't exist
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials
            if user_id:
                database.get_db().save_user_token(user_id, pickle.dumps(creds))
            else:
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
        else:
            # Create credentials from environment variables
            client_id = os.environ.get('GOOGLE_CLIENT_ID')
            client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                raise Exception("Gmail credentials not found in environment variables")
            
            # Check for explicitly configured redirect URI
            configured_redirect = os.environ.get('GMAIL_REDIRECT_URI')
            
            if configured_redirect:
                redirect_uri = configured_redirect
            elif os.environ.get('REPLIT_DEV_DOMAIN'):
                replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
                redirect_uri = f'https://{replit_domain}/gmail/callback'
            else:
                # Fallback to localhost on configured port (default 8080)
                port = os.environ.get('PORT', '8080')
                api_version = os.environ.get('API_VERSION', 'v1')
                redirect_uri = f'http://localhost:{port}/api/{api_version}/gmail/callback'
            
            print(f"DEBUG: Using OAuth Redirect URI: {redirect_uri}")
            
            # For web flow, we need redirect URI
            client_config = {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
            
            # We don't save here yet, as we need the flow to complete
            return None, flow, None # No token file path needed anymore
        
        # Save credentials for next time (re-save if valid)
        if user_id and creds and creds.valid:
            database.get_db().save_user_token(user_id, pickle.dumps(creds))
    
    return creds, None, None

def get_gmail_service(user_id=None):
    """Get authenticated Gmail API service for a specific user"""
    creds, flow, _ = get_credentials(user_id)
    
    if flow:
        return None, flow, None
    
    return build('gmail', 'v1', credentials=creds), None, None

def get_user_info(creds):
    """Get user information from Google"""
    try:
        import requests
        headers = {'Authorization': f'Bearer {creds.token}'}
        response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return None

def search_emails(service, broker, days_back=180):
    """Search for emails from a specific broker"""
    pattern = BROKER_PATTERNS.get(broker.lower())
    if not pattern:
        return []
    
    # Calculate date for search
    date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
    
    # Build search query
    query_parts = [
        f'from:{pattern["from"]}',
        'has:attachment',
        f'after:{date_from}'
    ]
    
    if pattern['subject']:
        # Use quoted subject for partial match
        query_parts.append(f'subject:"{pattern["subject"]}"')
    
    query = ' '.join(query_parts)
    
    print(f"=== Gmail Search Debug ===")
    print(f"Broker: {broker.upper()}")
    print(f"Search Query: {query}")
    print(f"Searching emails from {date_from} onwards...")
    
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        print(f"Found {len(messages)} messages matching query")
        
        # If no results with subject filter, try without it
        if not messages and pattern['subject']:
            print(f"No results with subject filter, trying without subject...")
            query_parts_no_subject = [
                f'from:{pattern["from"]}',
                'has:attachment',
                f'after:{date_from}'
            ]
            query_no_subject = ' '.join(query_parts_no_subject)
            print(f"Retry Query: {query_no_subject}")
            
            results = service.users().messages().list(
                userId='me',
                q=query_no_subject,
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            print(f"Found {len(messages)} messages without subject filter")
        
        return messages
    except Exception as e:
        print(f"Error searching emails: {e}")
        return []

def get_message_details(service, msg_id):
    """Get email message details"""
    try:
        message = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()
        
        headers = message['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
        
        return {
            'id': msg_id,
            'subject': subject,
            'from': sender,
            'date': date,
            'payload': message['payload']
        }
    except Exception as e:
        print(f"Error getting message: {e}")
        return None

def download_attachment(service, msg_id, attachment_id, filename, store_dir):
    """Download a specific attachment"""
    try:
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=msg_id,
            id=attachment_id
        ).execute()
        
        file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
        filepath = os.path.join(store_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(file_data)
        
        return filepath
    except Exception as e:
        print(f"Error downloading attachment: {e}")
        return None

def get_attachments(service, msg_id, broker, store_dir='temp_downloads'):
    """Get attachments from a message"""
    try:
        message = service.users().messages().get(
            userId='me',
            id=msg_id
        ).execute()
        
        if not os.path.exists(store_dir):
            os.makedirs(store_dir)
        
        pattern = BROKER_PATTERNS.get(broker.lower())
        file_ext = pattern['file_pattern'] if pattern else '.pdf'
        
        attachments = []
        parts = [message['payload']]
        
        while parts:
            part = parts.pop()
            
            if part.get('parts'):
                parts.extend(part['parts'])
            
            if part.get('filename'):
                filename = part['filename']
                
                # Filter by file extension
                if not filename.lower().endswith(file_ext):
                    continue
                
                if 'data' in part['body']:
                    data = part['body']['data']
                    file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                    filepath = os.path.join(store_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(file_data)
                else:
                    att_id = part['body']['attachmentId']
                    filepath = download_attachment(service, msg_id, att_id, filename, store_dir)
                
                if filepath:
                    attachments.append({
                        'filename': filename,
                        'path': filepath,
                        'size': os.path.getsize(filepath)
                    })
        
        return attachments
    except Exception as e:
        print(f"Error getting attachments: {e}")
        return []

def get_latest_statement(service, broker):
    """Get the latest portfolio statement for a broker"""
    messages = search_emails(service, broker)
    
    if not messages:
        return None
    
    # Get the most recent message
    latest_msg = messages[0]
    msg_details = get_message_details(service, latest_msg['id'])
    
    if not msg_details:
        return None
    
    # Download attachments - don't use context manager to keep files available
    temp_dir = tempfile.mkdtemp()
    attachments = get_attachments(service, latest_msg['id'], broker, temp_dir)
    
    if attachments:
        return {
            'email': msg_details,
            'attachment': attachments[0],
            'temp_dir': temp_dir  # Return temp dir so caller can clean up
        }
    
    return None
