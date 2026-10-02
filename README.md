# Docker Auto-Login & Hybrid Deployment (Webhook + Watcher)

```
                 GitHub (Punith887/docker-auto-login)
                 /                                  \
                /                                    \
      Webhook (Instant Push)               Watcher (Fail-safe Poller)
      https://smee.io/wobQBSrxNGXlWOf      Every 10 seconds
                \                                    /
                 \                                  /
                  └───────────────┬────────────────┘
                                  ▼
                         YOUR LAPTOP SERVER
                        (auto_sync.py Daemon)
                                  │
                                  ▼
                        Docker Compose Build
                     (login-app on Port 5000)
                                  │
                             Wi-Fi / LAN
                                  │
                   ┌──────────────┼──────────────┐
                   ▼              ▼              ▼
                Laptop 1       Laptop 2       Laptop 30
```

---

## 1. Webhook URL for Your GitHub Repository

Add this webhook to your GitHub repository:
- **Direct Webhook Settings Link**:  
  https://github.com/Punith887/docker-auto-login/settings/hooks/new

### Webhook Configuration Details:
| Field | Value |
|---|---|
| **Payload URL** | `https://smee.io/wobQBSrxNGXlWOf` |
| **Content type** | `application/json` |
| **Secret** | *(Leave empty)* |
| **SSL verification** | `Enable SSL verification` |
| **Which events?** | `Just the push event` (or select `Pushes` and `Pull requests`) |
| **Active** | Checked `[x]` |

---

## 2. Start the Service on Your Laptop (Host)

Double-click `run_sync.bat` or run:
```powershell
python auto_sync.py
```

### What `auto_sync.py` Does:
1. **Webhook Listener**: Listens to the public Smee stream in real time. The moment code is pushed to GitHub, deployment triggers immediately.
2. **Local Webhook Receiver**: Listens on `http://localhost:9000/webhook` for local tests or tools.
3. **Watcher Fail-safe**: Polls GitHub `origin/main` every 10 seconds in case a webhook is missed.
4. **Auto-Deploy**: Performs `git fetch origin main && git reset --hard origin/main` and runs `docker compose up -d --build`.

---

## 3. Test the Webhook Locally

To verify deployment without pushing to GitHub, open a separate terminal and run:
```powershell
python test_webhook.py
```

---

## 4. LAN Access for Developers

All developers on your Wi-Fi network open:
```text
http://192.168.1.55:5000
```
- **Health Check**: `http://192.168.1.55:5000/health`
- **Default Credentials**: `admin` / `1234`
