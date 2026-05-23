import subprocess
import json
import os

KUBECONFIG = "f:/am-repos/am-repos/VPS-Infra/kubeconfig.vps"
CONTEXT = "kind-am-preprod"

def run_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout

print("Syncing secrets from am-apps-preprod to am-apps-dev...")

# 1. Get the secret from preprod
get_cmd = [
    "kubectl", "--kubeconfig", KUBECONFIG, "--context", CONTEXT,
    "get", "secret", "github-registry-secret", "-n", "am-apps-preprod", "-o", "json"
]
secret_json = run_command(get_cmd)

if secret_json:
    secret_data = json.loads(secret_json)
    
    # 2. Sync to "github-registry-secret" in dev
    secret_names = ["github-registry-secret", "regcred"]
    
    for name in secret_names:
        print(f"Applying secret '{name}' in am-apps-dev...")
        new_secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": name
            },
            "type": secret_data["type"],
            "data": secret_data["data"]
        }
        
        temp_file = f"temp_{name}_secret.json"
        with open(temp_file, "w") as f:
            json.dump(new_secret, f)
        
        apply_cmd = [
            "kubectl", "--kubeconfig", KUBECONFIG, "--context", CONTEXT,
            "apply", "-n", "am-apps-dev", "-f", temp_file
        ]
        print(run_command(apply_cmd))
        
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    print("SUCCESS: Synced both github-registry-secret and regcred secrets to am-apps-dev namespace!")
else:
    print("FAILED: Could not retrieve secret from am-apps-preprod.")
