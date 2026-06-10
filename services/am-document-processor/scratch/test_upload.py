import requests
import json

url = "https://am-dev.asrax.in/am/document/v1/documents/process"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODExODUwNjAsImlhdCI6MTc4MTA5ODY2MCwic3ViIjoiYjc1NzQzYzktZmUwZS00YzU0LThlZTAtOGRhMzUwY2MyN2IzIiwidXNlcm5hbWUiOiJzc2QyNjU4QGdtYWlsLmNvbSIsImVtYWlsIjoic3NkMjY1OEBnbWFpbC5jb20iLCJzY29wZXMiOlsicmVhZCIsIndyaXRlIl19.Fqr-2_SUshboxpLaR7e7FcHdgafJMXBfQSCsjd2sMAk"
user_id = "b75743c9-fe0e-4c54-8ee0-8da350cc27b3"

headers = {
    "Authorization": f"Bearer {token}",
    "X-User-ID": user_id
}

files = {
    "file": ("a1338c6d-d30e-4595-b9f4-bdb4bd2fec33.xlsx", open("docs/a1338c6d-d30e-4595-b9f4-bdb4bd2fec33.xlsx", "rb"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
}

data = {
    "brokerType": "ANGEL_ONE",
    "documentType": "TRADE_EQ"
}

print("Uploading file...")
response = requests.post(url, headers=headers, files=files, data=data)
print(f"Status Code: {response.statusCode if hasattr(response, 'statusCode') else response.status_code}")
try:
    print(json.dumps(response.json(), indent=2))
except Exception:
    print(response.text)
