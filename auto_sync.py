import os
import sys
import time
import json
import queue
import socket
import threading
import subprocess
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
BRANCH = "main"
REMOTE = "origin"
WATCHER_INTERVAL = 10     # seconds for fallback poller
WEBHOOK_PORT = 9000       # local port for webhook HTTP listener
APP_PORT = 5000           # port where Docker app runs

# Public Webhook URL generated for GitHub
WEBHOOK_URL = "https://smee.io/wobQBSrxNGXlWOf"

# Thread-safe queue for deployment triggers
deploy_queue = queue.Queue()


def get_local_ip():
    """Retrieve primary local IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def run_cmd(cmd):
    """Run shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_commit_hash(ref):
    code, out, _ = run_cmd(f"git rev-parse {ref}")
    return out if code == 0 else None


def get_commit_message(ref):
    code, out, _ = run_cmd(f'git log -1 --pretty=format:"%h - %s (%an)" {ref}')
    return out if code == 0 else ""


# ==========================================
# DEPLOYMENT ENGINE
# ==========================================
def deploy(source="Manual", details=""):
    """Fetch latest changes and rebuild Docker container."""
    now = datetime.now().strftime("%H:%M:%S")
    print("\n" + "=" * 65)
    print(f"[{now}] DEPLOY TRIGGERED VIA: {source}")
    if details:
        print(f"Details: {details}")
    print("=" * 65)

    # 1. Cleanly sync git repository to origin/main
    print(f"[{now}] Syncing code from GitHub {REMOTE}/{BRANCH}...")
    code, out, err = run_cmd(f"git fetch {REMOTE} {BRANCH} && git reset --hard {REMOTE}/{BRANCH}")
    if code != 0:
        print(f"[ERROR] Git sync failed: {err}")
        return False
    print(out)

    # 2. Rebuild and restart docker container
    print(f"\n[{now}] Rebuilding and restarting Docker container...")
    code, out, err = run_cmd("docker compose up -d --build")
    if code != 0:
        print(f"[ERROR] Docker compose failed: {err}")
        return False
    print(out)

    local_ip = get_local_ip()
    latest_commit = get_commit_message("HEAD")
    print("\n" + "=" * 65)
    print(f"[SUCCESS] Deployment complete at {datetime.now().strftime('%H:%M:%S')}!")
    print(f"-> Active Commit  : {latest_commit}")
    print(f"-> Local Access   : http://localhost:{APP_PORT}")
    print(f"-> LAN / Friends  : http://{local_ip}:{APP_PORT}")
    print("=" * 65 + "\n")
    return True


def deployment_worker():
    """Consumes deployment queue with debouncing."""
    while True:
        source, details = deploy_queue.get()
        # Drain any duplicate triggers in queue within 2 seconds
        time.sleep(1)
        while not deploy_queue.empty():
            try:
                deploy_queue.get_nowait()
                deploy_queue.task_done()
            except queue.Empty:
                break

        deploy(source, details)
        deploy_queue.task_done()


# ==========================================
# WEBHOOK CHANNEL 1: SMEE.IO SSE LISTENER
# ==========================================
def smee_sse_listener():
    """Connects to Smee.io SSE stream to receive real-time GitHub Webhook payloads."""
    while True:
        try:
            req = urllib.request.Request(
                WEBHOOK_URL,
                headers={
                    "Accept": "text/event-stream",
                    "User-Agent": "DockerAutoLogin-Webhook/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                print(f"[*] Connected to Smee Webhook stream: {WEBHOOK_URL}")
                for line in resp:
                    text = line.decode("utf-8").strip()
                    if text.startswith("data:"):
                        raw = text[5:].strip()
                        if not raw or raw == "{}":
                            continue
                        try:
                            event_data = json.loads(raw)
                            if not isinstance(event_data, dict):
                                continue

                            event_type = event_data.get("x-github-event", "event")
                            body = event_data.get("body", {})

                            if event_type == "ping":
                                zen = body.get("zen", "GitHub Webhook Connected!")
                                print(f"\n[WEBHOOK] Ping received from GitHub: {zen}")
                                continue

                            # Detect push or merged PR
                            ref = body.get("ref", "")
                            action = body.get("action", "")
                            is_merged_pr = (action == "closed" and body.get("pull_request", {}).get("merged") is True)

                            if f"refs/heads/{BRANCH}" in ref or is_merged_pr:
                                sender = body.get("sender", {}).get("login", "unknown")
                                head_commit = body.get("head_commit", {})
                                msg = head_commit.get("message", f"{event_type} on {BRANCH}")
                                print(f"\n[WEBHOOK] Instant GitHub event: {event_type} by @{sender}")
                                deploy_queue.put(("GitHub Webhook (Instant)", f"Event: {event_type} | Author: {sender} | Msg: {msg.splitlines()[0] if msg else ''}"))

                        except Exception as parse_err:
                            pass
        except Exception:
            # Reconnect after brief pause if stream disconnects
            time.sleep(4)


# ==========================================
# WEBHOOK CHANNEL 2: LOCAL HTTP SERVER
# ==========================================
class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        event_type = self.headers.get("X-GitHub-Event", "push")

        try:
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            data = {}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok","received":true}\n')

        ref = data.get("ref", "")
        if not ref or f"refs/heads/{BRANCH}" in ref or data.get("action") == "closed":
            sender = data.get("sender", {}).get("login", "local-test")
            print(f"\n[LOCAL WEBHOOK] Received POST on port {WEBHOOK_PORT} (event: {event_type})")
            deploy_queue.put(("Local Webhook HTTP", f"Event: {event_type} from {self.client_address[0]}"))

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        status_info = {
            "service": "Docker Auto Login Webhook Listener",
            "webhook_url": WEBHOOK_URL,
            "branch": f"{REMOTE}/{BRANCH}",
            "status": "RUNNING"
        }
        self.wfile.write(json.dumps(status_info, indent=2).encode("utf-8"))

    def log_message(self, format, *args):
        # Silence default HTTP access logs to keep terminal clean
        return


def local_webhook_server():
    server = HTTPServer(("0.0.0.0", WEBHOOK_PORT), WebhookHandler)
    server.serve_forever()


# ==========================================
# WATCHER CHANNEL: PERIODIC GIT POLLER
# ==========================================
def watcher():
    """Polls GitHub remote periodically as a fail-safe backup."""
    last_known_hash = get_commit_hash("HEAD")
    while True:
        try:
            time.sleep(WATCHER_INTERVAL)
            code, _, _ = run_cmd(f"git fetch {REMOTE} {BRANCH}")
            if code != 0:
                continue

            remote_hash = get_commit_hash(f"{REMOTE}/{BRANCH}")
            local_hash = get_commit_hash("HEAD")

            if remote_hash and local_hash != remote_hash:
                remote_msg = get_commit_message(f"{REMOTE}/{BRANCH}")
                print(f"\n[WATCHER] Detected new commit on {REMOTE}/{BRANCH} via polling:")
                print(f"          {remote_msg}")
                deploy_queue.put(("Watcher (Fail-safe Poller)", remote_msg))
                last_known_hash = remote_hash
            else:
                sys.stdout.write(f"\r[{datetime.now().strftime('%H:%M:%S')}] Active: Webhook live + Watcher monitoring... ")
                sys.stdout.flush()

        except Exception as e:
            time.sleep(WATCHER_INTERVAL)


# ==========================================
# MAIN ENTRYPOINT
# ==========================================
def main():
    local_ip = get_local_ip()
    print("=" * 65)
    print(" DOCKER HYBRID AUTO-DEPLOY (WEBHOOK + WATCHER)")
    print("=" * 65)
    print(f"Target Branch      : {REMOTE}/{BRANCH}")
    print(f"Public Webhook URL : {WEBHOOK_URL}")
    print(f"Local Webhook Port : http://localhost:{WEBHOOK_PORT}/webhook")
    print(f"Watcher Interval   : Every {WATCHER_INTERVAL} seconds")
    print(f"Your Wi-Fi/LAN IP  : {local_ip}")
    print(f"LAN Application URL: http://{local_ip}:{APP_PORT}")
    print("=" * 65)

    # 1. Start deployment worker thread
    t_worker = threading.Thread(target=deployment_worker, daemon=True)
    t_worker.start()

    # 2. Start Smee SSE Webhook listener thread
    t_smee = threading.Thread(target=smee_sse_listener, daemon=True)
    t_smee.start()

    # 3. Start Local HTTP Webhook receiver thread
    t_http = threading.Thread(target=local_webhook_server, daemon=True)
    t_http.start()

    # 4. Start Fallback Git Watcher thread
    t_watcher = threading.Thread(target=watcher, daemon=True)
    t_watcher.start()

    print("[*] All services running! Paste the Webhook URL into GitHub settings.")
    print("[*] Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Shutting down services.")


if __name__ == "__main__":
    main()
