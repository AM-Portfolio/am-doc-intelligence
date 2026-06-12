import requests
import json

url = "http://localhost:8081/v1/documents/process"
user_id = "b75743c9-fe0e-4c54-8ee0-8da350cc27b3"

headers = {
    "X-User-ID": user_id
}

def upload_file(file_path, doc_type, broker_type):
    print(f"\nUploading {file_path} as {doc_type} for {broker_type}...")
    files = {
        "file": (file_path.split("/")[-1], open(file_path, "rb"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    data = {
        "brokerType": broker_type,
        "documentType": doc_type
    }
    response = requests.post(url, headers=headers, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    try:
         print(json.dumps(response.json(), indent=2))
    except Exception:
         print(response.text)

# Test 1: MStock Portfolio
upload_file("docs/Portfolio_report_1781113687706.xlsx", "STOCK_PORTFOLIO", "MSTOCK")

# Test 2: MStock Trade History
upload_file("docs/trade_history2025-04-01_2026-03-31_1781113567782.xlsx", "TRADE_EQ", "MSTOCK")
