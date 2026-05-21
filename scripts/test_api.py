import requests
import os
import argparse
import json

# Token provided by user
USER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NzkwMDcyNzUsImlhdCI6MTc3ODkyMDg3NSwic3ViIjoiYjc1NzQzYzktZmUwZS00YzU0LThlZTAtOGRhMzUwY2MyN2IzIiwidXNlcm5hbWUiOiJzc2QyNjU4QGdtYWlsLmNvbSIsImVtYWlsIjoic3NkMjY1OEBnbWFpbC5jb20iLCJzY29wZXMiOlsicmVhZCIsIndyaXRlIl19.uqaDH_iDEZeSgnjOD7Q5gnG3MrE8jnxzhrPgYQjUUpU"
USER_ID = "b75743c9-fe0e-4c54-8ee0-8da350cc27b3"

def test_document_processor(file_path, broker_type="ZERODHA", document_type="STOCK_PORTFOLIO", env="preprod", password=None):
    # Determine base URL based on environment
    if env == "local":
        base_url = "http://localhost:8080/v1/documents"
    else:
        base_url = "https://am.asrax.in/doc/processor/v1/documents"
    
    upload_url = f"{base_url}/process"
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    headers = {
        'X-User-ID': USER_ID,
        'Authorization': f'Bearer {USER_TOKEN}'
    }

    # Prepare multipart form data
    files = {
        'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/octet-stream')
    }
    
    data = {
        'brokerType': broker_type,
        'documentType': document_type
    }
    
    if password:
        data['password'] = password

    print(f"Sending {os.path.basename(file_path)} to {upload_url}...")
    print(f"Broker: {broker_type} | Env: {env} | User: {USER_ID}")
    
    try:
        response = requests.post(upload_url, headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            print("Success!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Failed with status code: {response.status_code}")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
                
    except Exception as e:
        print(f"Error connecting to API: {str(e)}")
    finally:
        files['file'][1].close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test AM Document Processor API")
    parser.add_argument("file", help="Path to the document file (xlsx, pdf, etc.)")
    parser.add_argument("--broker", default="ZERODHA", help="Broker type (e.g., ZERODHA, UPSTOX)")
    parser.add_argument("--type", default="STOCK_PORTFOLIO", help="Document type")
    parser.add_argument("--env", choices=["local", "preprod"], default="preprod", help="Environment to test against")
    parser.add_argument("--password", help="Password for encrypted PDF files")
    
    args = parser.parse_args()
    
    test_document_processor(
        args.file, 
        broker_type=args.broker, 
        document_type=args.type, 
        env=args.env,
        password=args.password
    )
