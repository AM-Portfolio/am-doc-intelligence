import os
import subprocess
import requests
import json
import jwt
from datetime import datetime, timedelta

# Configurations
BASE_URL = "https://am-dev.asrax.in/doc/processor/v1/documents"
USER_ID = "b75743c9-fe0e-4c54-8ee0-8da350cc27b3"
DOCS_DIR = "f:/am-repos/am-repos/am-doc-intelligence/services/am-document-processor/docs"

# 1. Dynamically retrieve the JWT secret from Kubernetes or use the active dev secret
def get_jwt_secret():
    try:
        cmd = [
            "kubectl", "--kubeconfig", "f:/am-repos/am-repos/VPS-Infra/kubeconfig.vps", "-n", "am-apps-dev",
            "exec", "deploy/am-document-processor", "-c", "am-document-processor", "--", "cat", "/vault/secrets/auth"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if "export JWT_SECRET=" in line:
                return line.split('="')[1].rstrip('"')
    except Exception:
        pass
    # Fallback to current active secret
    return "3ced460bdc463104a2081d79f915ac4f"

# 2. Generate a valid mock JWT token
def generate_token(secret, user_id):
    payload = {
        "sub": user_id,
        "userId": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iss": "am-auth-service"
    }
    return jwt.encode(payload, secret, algorithm="HS256")

# 3. List of files to test mapped to correct broker & docType
TEST_FILES = [
    {"file": "Dhan_Portfolio_EQ_01-05-2026.xlsx", "broker": "DHAN", "type": "STOCK_PORTFOLIO"},
    {"file": "Dhan_Portfolio_ETF_01-05-2026.xlsx", "broker": "DHAN", "type": "STOCK_PORTFOLIO"},
    {"file": "Stocks_Holdings_Statement_3060484652_2026-01-21_1769102041357.xlsx", "broker": "GROW", "type": "STOCK_PORTFOLIO"},
    {"file": "Stocks_Holdings_Statement_3060484652_2026-02-07_1770558733163.xlsx", "broker": "GROW", "type": "STOCK_PORTFOLIO"},
    {"file": "Stocks_Order_History_3060484652_2020-04-01_2026-01-21_1769101861896.xlsx", "broker": "GROW", "type": "TRADE_EQ"},
    {"file": "Stocks_Order_History_3060484652_2020-04-01_2026-02-07_1770557386613.xlsx", "broker": "GROW", "type": "TRADE_EQ"},
    {"file": "holdings-BKJ665 (2).xlsx", "broker": "ZERODHA", "type": "STOCK_PORTFOLIO"},
    {"file": "holdings.csv", "broker": "ZERODHA", "type": "STOCK_PORTFOLIO"},
    {"file": "tradebook-BKJ665-EQ (1).xlsx", "broker": "ZERODHA", "type": "TRADE_EQ"},
    {"file": "tradebook-BKJ665-FO.xlsx", "broker": "ZERODHA", "type": "TRADE_FNO"},
    {"file": "trade_history2024-06-21_2026-02-11_1770823206679.xlsx", "broker": "MSTOCK", "type": "TRADE_EQ"}
]

def run_tests():
    secret = get_jwt_secret()
    token = generate_token(secret, USER_ID)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-ID": USER_ID
    }
    
    print("\n" + "="*80)
    print("RUNNING BATCH STATEMENT PARSING INTEGRATION TESTS (ALL BROKERS)")
    print("="*80)
    
    success_count = 0
    
    for item in TEST_FILES:
        file_name = item["file"]
        broker = item["broker"]
        doc_type = item["type"]
        file_path = os.path.join(DOCS_DIR, file_name)
        
        print(f"\n[Test] File: {file_name}")
        print(f"       Broker: {broker} | Type: {doc_type}")
        
        if not os.path.exists(file_path):
            print(f"       Status: FAILED - Local file not found at path {file_path}")
            continue
            
        data = {
            "documentType": doc_type,
            "brokerType": broker
        }
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                response = requests.post(f"{BASE_URL}/process", headers=headers, data=data, files=files)
                
            if response.status_code == 200:
                res_data = response.json()
                records = res_data.get("data", [])
                print(f"       Status: SUCCESS [OK] ({len(records)} parsed rows)")
                if records:
                    print(f"       Sample Record: {records[0]}")
                success_count += 1
            else:
                print(f"       Status: FAILED [FAIL] (HTTP {response.status_code})")
                print(f"       Error: {response.text}")
        except Exception as e:
            print(f"       Status: FAILED [FAIL] (Exception: {e})")
            
    print("\n" + "="*80)
    print(f"SUMMARY: {success_count}/{len(TEST_FILES)} tests succeeded!")
    print("="*80)

if __name__ == "__main__":
    run_tests()
