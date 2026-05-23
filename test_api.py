import requests
import json
import os
import time
import argparse
from datetime import datetime, timedelta

# Configuration
DEFAULT_BASE_URL = "http://localhost:8089"
DEFAULT_USER_ID = "user123"
# Default secret from application.yml
DEFAULT_SECRET = "user-secret-key-min-32-characters-long-required-here"

def generate_token(secret, user_id):
    """
    Generates a mock JWT token for testing.
    Requires 'PyJWT' (pip install PyJWT).
    """
    try:
        import jwt
        payload = {
            "sub": user_id,
            "userId": user_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iss": "am-auth-service"
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token
    except ImportError:
        print("\n[!] Warning: 'PyJWT' not found. Cannot generate fresh tokens.")
        print("[!] Run: pip install PyJWT")
        return None

def get_types(base_url):
    """Test the public 'types' endpoint."""
    print(f"\n--- Testing Supported Types (Public) ---")
    
    # Handle different URL formats
    if "/documents" in base_url:
        url = f"{base_url}/types"
    else:
        url = f"{base_url}/api/v1/documents/types"
        
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Supported Types: {response.json()}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

def process_document(base_url, token, user_id, file_path, doc_type, portfolio_id=None, broker=None, password=None):
    """Test the protected 'process' endpoint."""
    print(f"\n--- Testing Document Process (Protected) ---")
    if not token:
        print("[!] Skipping: No token available.")
        return

    # Handle different URL formats
    if "/documents" in base_url:
        url = f"{base_url}/process"
    else:
        url = f"{base_url}/api/v1/documents/process"
        
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-ID": user_id
    }
    
    if not os.path.exists(file_path):
        print(f"[!] Error: File not found at {file_path}")
        return

    data = {
        "documentType": doc_type
    }
    if portfolio_id:
        data["portfolioId"] = portfolio_id
    if broker:
        data["brokerType"] = broker
    if password:
        data["password"] = password

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(url, headers=headers, data=data, files=files)
            
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Test Document Processor API")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--user", default=DEFAULT_USER_ID, help=f"User ID (default: {DEFAULT_USER_ID})")
    parser.add_argument("--secret", default=DEFAULT_SECRET, help="JWT Secret")
    parser.add_argument("--file", help="Path to a document to upload")
    parser.add_argument("--type", default="STOCK_PORTFOLIO", help="Document type (e.g. STOCK_PORTFOLIO)")
    parser.add_argument("--token", help="Override with existing JWT token")
    parser.add_argument("--broker", help="Broker type (e.g. ZERODHA, ANGEL_ONE, GROWW)")
    parser.add_argument("--password", help="Password for encrypted documents")

    args = parser.parse_args()

    # 1. Get supported types (Public)
    get_types(args.url)

    # 2. Get or Generate Token
    token = args.token
    if not token:
        token = generate_token(args.secret, args.user)

    # 3. Process Document if file is provided
    if args.file:
        process_document(args.url, token, args.user, args.file, args.type, broker=args.broker, password=args.password)
    else:
        print("\n[i] Tip: Provide a --file argument to test document upload.")
        print("    Example: python test_api.py --file ./docs/sample.xlsx --type STOCK_PORTFOLIO")

if __name__ == "__main__":
    main()
