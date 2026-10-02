import json
import urllib.request
import sys

# Target local webhook or public smee webhook
TARGET_URL = "http://localhost:9000/webhook"
if len(sys.argv) > 1 and sys.argv[1] == "--smee":
    TARGET_URL = "https://smee.io/wobQBSrxNGXlWOf"

payload = {
    "ref": "refs/heads/main",
    "sender": {
        "login": "test-developer"
    },
    "head_commit": {
        "id": "abc12345",
        "message": "feat: test webhook deployment trigger",
        "author": {"name": "Test Developer"}
    },
    "repository": {
        "full_name": "Punith887/docker-auto-login"
    }
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    TARGET_URL,
    data=data,
    headers={
        "Content-Type": "application/json",
        "X-GitHub-Event": "push",
        "User-Agent": "GitHub-Hookshot/test"
    }
)

print(f"[*] Sending mock GitHub Webhook to: {TARGET_URL}...")
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"[SUCCESS] Status: {resp.status}")
        print("Webhook delivered successfully!")
except Exception as e:
    print(f"[ERROR] Failed to send webhook: {e}")
