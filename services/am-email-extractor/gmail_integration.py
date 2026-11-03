import os
import base64
import json
import logging
import pickle
import tempfile
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Allow OAuth over HTTP when behind a reverse proxy (like Replit)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

# Code defaults — overridden at startup by Vault/env GMAIL_BROKER_PATTERNS_JSON
DEFAULT_BROKER_PATTERNS = {
    'zerodha': {
        'from': 'zerodha.net',
        'subject': 'Holding Statement',
        'file_pattern': ['.pdf'],
    },
    'groww': {
        'from': 'groww.in',
        'subject': 'Holding Statement',
        'file_pattern': ['.pdf'],
    },
    'dhan': {
        'from': 'statements@dhan.co',
        'subject': 'Demat Holding Summary',
        'file_pattern': ['.pdf', '.xlsx', '.xls'],
    },
    'mstock': {
        'from': 'mstock.com',
        'subject': 'TRANSACTION STATEMENT',
        'file_pattern': ['.pdf'],
    },
    'angleone': {
        'from': 'angelone.in',
        'subject': 'Holdings',
        'file_pattern': ['.xlsx'],
    },
    # CDSL CAS / NPS — real mailboxes use statement relays (not corporate domains).
    # Override via Vault GMAIL_BROKER_PATTERNS_JSON if senders differ.
    'cdsl': {
        'from': 'cdslstatement.com',  # eCAS@cdslstatement.com
        'subject': 'Consolidated Account Statement',
        'file_pattern': ['.pdf'],
    },
    'nps': {
        'from': 'proteantech.in',  # nps-statements@mailer.proteantech.in
        'subject': 'Monthly Transaction Statement',
        'file_pattern': ['.pdf'],
    },
}


def _normalize_pattern(raw: dict) -> dict:
    """Normalize one broker pattern; file_pattern always a list of lowercase extensions."""
    fp = raw.get('file_pattern', ['.pdf'])
    if isinstance(fp, str):
        exts = [fp]
    else:
        exts = list(fp or ['.pdf'])
    exts = [e if str(e).startswith('.') else f'.{e}' for e in exts]
    exts = [str(e).lower() for e in exts]
    return {
        'from': (raw.get('from') or '').strip(),
        'subject': (raw.get('subject') or '').strip(),
        'file_pattern': exts,
    }


def load_broker_patterns() -> dict:
    """Merge Vault/env JSON over code defaults. Change Vault → restart pod."""
    patterns = {
        k: _normalize_pattern(v) for k, v in DEFAULT_BROKER_PATTERNS.items()
    }
    raw = (os.environ.get('GMAIL_BROKER_PATTERNS_JSON') or '').strip()
    if not raw:
        logger.info(
            'GMAIL_BROKER_PATTERNS_JSON unset; using code defaults for brokers: %s',
            sorted(patterns.keys()),
        )
        return patterns
    try:
        overlay = json.loads(raw)
        if not isinstance(overlay, dict):
            raise ValueError('GMAIL_BROKER_PATTERNS_JSON must be a JSON object')
        for broker, cfg in overlay.items():
            if not isinstance(cfg, dict):
                continue
            key = str(broker).lower().strip()
            base = patterns.get(key, {})
            merged = {**base, **cfg}
            patterns[key] = _normalize_pattern(merged)
        summary = {
            k: {
                'from': v.get('from'),
                'subject': v.get('subject'),
                'file_pattern': v.get('file_pattern'),
            }
            for k, v in sorted(patterns.items())
        }
        logger.info('Loaded broker mail filters from GMAIL_BROKER_PATTERNS_JSON: %s', summary)
        print(f'DEBUG: Loaded broker mail filters from Vault/env: {summary}')
    except Exception as e:
        logger.error(
            'Invalid GMAIL_BROKER_PATTERNS_JSON (%s); using code defaults',
            e,
        )
        print(f'DEBUG: Invalid GMAIL_BROKER_PATTERNS_JSON ({e}); using code defaults')
    return patterns


BROKER_PATTERNS = load_broker_patterns()


def get_credentials(user_id=None, mailbox=None, *, force_new_flow=False):
    """Get Gmail API credentials for a user mailbox (optional email).

    force_new_flow=True skips existing tokens and starts OAuth (add another mailbox).
    """
    creds = None
    import database
    mailbox_email = (mailbox or '').strip().lower() or None

    if force_new_flow:
        creds = None
    elif user_id:
        try:
            token_data = database.get_db().get_user_token(user_id, email=mailbox_email)
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
                email_for_save = mailbox_email
                if not email_for_save:
                    info = get_user_info(creds)
                    email_for_save = (info or {}).get('email')
                database.get_db().save_user_token(
                    user_id, pickle.dumps(creds), email=email_for_save
                )
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
            return None, flow, None  # No token file path needed anymore

        # Save credentials for next time (re-save if valid)
        if user_id and creds and creds.valid:
            email_for_save = mailbox_email
            if not email_for_save:
                info = get_user_info(creds)
                email_for_save = (info or {}).get('email')
            database.get_db().save_user_token(
                user_id, pickle.dumps(creds), email=email_for_save
            )

    return creds, None, None


def get_gmail_service(user_id=None, mailbox=None, *, force_new_flow=False):
    """Get authenticated Gmail API service for a user mailbox."""
    creds, flow, _ = get_credentials(
        user_id, mailbox=mailbox, force_new_flow=force_new_flow
    )

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

def _list_messages(service, query: str, max_results: int = 10):
    print(f"Search Query: {query}")
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results,
    ).execute()
    messages = results.get('messages', [])
    print(f"Found {len(messages)} messages matching query")
    return messages


def search_emails(service, broker, days_back=180):
    """Search for emails from a specific broker.

    Order: from+subject → subject-only (correct when sender relay differs) →
    from-only. Avoids matching unrelated corporate notices on broad domains.
    """
    pattern = BROKER_PATTERNS.get(broker.lower())
    if not pattern:
        return []

    date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
    from_part = (pattern.get('from') or '').strip()
    subject = (pattern.get('subject') or '').strip()

    print(f"=== Gmail Search Debug ===")
    print(f"Broker: {broker.upper()}")
    print(f"Searching emails from {date_from} onwards...")

    try:
        if from_part and subject:
            messages = _list_messages(
                service,
                f'from:{from_part} has:attachment after:{date_from} subject:"{subject}"',
            )
            if messages:
                return messages

        # Subject-only: CDSL/NPS often come from statement relays, not corporate domains.
        if subject:
            print('No from+subject hits; trying subject-only…')
            messages = _list_messages(
                service,
                f'has:attachment after:{date_from} subject:"{subject}"',
            )
            if messages:
                return messages

        if from_part:
            print('No subject hits; trying from-only…')
            messages = _list_messages(
                service,
                f'from:{from_part} has:attachment after:{date_from}',
            )
            return messages

        return []
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
        internal_date_ms = message.get('internalDate')
        
        return {
            'id': msg_id,
            'subject': subject,
            'from': sender,
            'date': date,
            'internal_date_ms': internal_date_ms,
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


def _file_extensions_for_broker(broker: str) -> list:
    pattern = BROKER_PATTERNS.get((broker or '').lower())
    if not pattern:
        return ['.pdf']
    fp = pattern.get('file_pattern') or ['.pdf']
    if isinstance(fp, str):
        return [fp.lower() if fp.startswith('.') else f'.{fp.lower()}']
    return [str(e).lower() for e in fp]


def _filename_matches(filename: str, extensions: list) -> bool:
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in extensions)


def pick_extract_attachment(attachments: list):
    """Prefer PDF for extractors that use PAN-locked PDFs; else first attachment."""
    if not attachments:
        return None
    for att in attachments:
        name = (att.get('filename') or '').lower()
        if name.endswith('.pdf'):
            return att
    return attachments[0]


def get_attachments(service, msg_id, broker, store_dir='temp_downloads'):
    """Get attachments from a message (supports multiple file_pattern extensions)."""
    try:
        message = service.users().messages().get(
            userId='me',
            id=msg_id
        ).execute()
        
        if not os.path.exists(store_dir):
            os.makedirs(store_dir)
        
        extensions = _file_extensions_for_broker(broker)
        
        attachments = []
        parts = [message['payload']]
        
        while parts:
            part = parts.pop()
            
            if part.get('parts'):
                parts.extend(part['parts'])
            
            if part.get('filename'):
                filename = part['filename']
                
                if not _filename_matches(filename, extensions):
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
    """Get the latest portfolio statement for a broker.

    Walks search hits until a message with a matching attachment is found
    (skips unrelated PDFs / notice mail that share a broad from: domain).
    """
    messages = search_emails(service, broker)
    if not messages:
        return None

    subject_hint = (
        (BROKER_PATTERNS.get((broker or '').lower()) or {}).get('subject') or ''
    ).strip().lower()

    temp_dir = tempfile.mkdtemp()
    try:
        for msg in messages:
            msg_details = get_message_details(service, msg['id'])
            if not msg_details:
                continue
            if subject_hint:
                subj = (msg_details.get('subject') or '').lower()
                if subject_hint not in subj:
                    print(
                        f"Skip msg subject mismatch: {msg_details.get('subject')!r}"
                    )
                    continue
            attachments = get_attachments(service, msg['id'], broker, temp_dir)
            chosen = pick_extract_attachment(attachments)
            if chosen:
                return {
                    'email': msg_details,
                    'attachment': chosen,
                    'attachments': attachments,
                    'temp_dir': temp_dir,
                }
            print(
                f"Skip msg with no matching attachment: {msg_details.get('subject')!r}"
            )
    except Exception:
        # Caller still owns cleanup of temp_dir if we already returned; here abort.
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        raise

    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
    return None
