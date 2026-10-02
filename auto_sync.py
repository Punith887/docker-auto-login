import os
import sys
import time
import socket
import subprocess
from datetime import datetime

BRANCH = "main"
REMOTE = "origin"
POLL_INTERVAL = 5  # seconds
PORT = 5000


def get_local_ip():
    """Retrieve the primary local IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually send data; connects to arbitrary IP to resolve active interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def run_cmd(cmd):
    """Run shell command and return stdout as string."""
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
    """Get the commit hash for a git reference."""
    code, out, _ = run_cmd(f"git rev-parse {ref}")
    return out if code == 0 else None


def get_commit_message(ref):
    """Get one-line commit message."""
    code, out, _ = run_cmd(f"git log -1 --pretty=format:\"%h - %s (%an)\" {ref}")
    return out if code == 0 else ""


def deploy():
    """Pull latest code and rebuild docker container."""
    print("\n" + "=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] PULLING LATEST COMMITS FROM GITHUB...")
    print("=" * 60)

    # 1. Pull
    code, out, err = run_cmd(f"git pull {REMOTE} {BRANCH}")
    print(out)
    if code != 0:
        print(f"[ERROR] git pull failed: {err}")
        return False

    # 2. Rebuild and restart docker containers
    print("\n" + "-" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] REBUILDING DOCKER CONTAINER...")
    print("-" * 60)
    code, out, err = run_cmd("docker compose up -d --build")
    print(out)
    if code != 0:
        print(f"[ERROR] docker compose failed: {err}")
        return False

    local_ip = get_local_ip()
    print("\n" + "=" * 60)
    print(f"[SUCCESS] Auto-deployed successfully at {datetime.now().strftime('%H:%M:%S')}!")
    print(f"-> Local Access   : http://localhost:{PORT}")
    print(f"-> Friend's Access: http://{local_ip}:{PORT}")
    print("=" * 60 + "\n")
    return True


def main():
    local_ip = get_local_ip()
    print("=" * 60)
    print(" DOCKER AUTO-SYNC & AUTO-DEPLOY")
    print("=" * 60)
    print(f"Repository Branch : {REMOTE}/{BRANCH}")
    print(f"Poll Interval     : {POLL_INTERVAL} seconds")
    print(f"Your Wi-Fi/LAN IP : {local_ip}")
    print(f"Friend's URL      : http://{local_ip}:{PORT}")
    print("=" * 60)

    # Verify git repository
    code, _, _ = run_cmd("git status")
    if code != 0:
        print("[ERROR] Not in a git repository. Exiting.")
        sys.exit(1)

    # Verify docker compose is accessible
    code, out, _ = run_cmd("docker compose version")
    if code != 0:
        print("[ERROR] Docker Compose is not available. Please start Docker Desktop.")
        sys.exit(1)

    print("[*] Sync service started. Waiting for git pushes...\n")

    last_local_hash = get_commit_hash("HEAD")
    print(f"[*] Initial commit: {get_commit_message('HEAD')}")

    while True:
        try:
            # Fetch remote without merging
            code, _, err = run_cmd(f"git fetch {REMOTE} {BRANCH}")
            if code != 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] Fetch failed: {err}")
                time.sleep(POLL_INTERVAL)
                continue

            remote_hash = get_commit_hash(f"{REMOTE}/{BRANCH}")
            current_local_hash = get_commit_hash("HEAD")

            if remote_hash and current_local_hash != remote_hash:
                print(f"\n[!] New commit detected on {REMOTE}/{BRANCH}!")
                print(f"    Remote: {get_commit_message(f'{REMOTE}/{BRANCH}')}")
                success = deploy()
                if success:
                    last_local_hash = get_commit_hash("HEAD")
            else:
                # Up to date indicator
                sys.stdout.write(f"\r[{datetime.now().strftime('%H:%M:%S')}] In sync with GitHub. Monitoring... ")
                sys.stdout.flush()

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n[!] Auto-sync stopped by user.")
            break
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
