# Docker Auto-Login & LAN Deployment

```
Friend's Laptop
      │
      │ git push
      ▼
    GitHub
      │
      │ auto-sync (auto_sync.py)
      ▼
Your Laptop (192.168.1.55)
      │
      ├── Python (auto_sync.py polling origin/main)
      ├── Docker (docker-compose up -d --build)
      └── Login Website (Flask on port 5000)
             │
             │ Wi-Fi / LAN
             ▼
       Friend's Browser
       http://192.168.1.55:5000
```

---

## 1. Setup on Your Laptop (Host)

### Step 1: Start Docker Desktop
Ensure Docker Desktop is running.

### Step 2: Start the Auto-Sync Service
Run the auto-sync daemon in a terminal:
```bash
python auto_sync.py
```
*(Or double-click `run_sync.bat`)*

This script:
1. Detects your local Wi-Fi IP (e.g., `192.168.1.55`).
2. Checks GitHub (`origin/main`) every 5 seconds.
3. When your friend pushes new code, it automatically pulls changes (`git pull`) and rebuilds the container (`docker compose up -d --build`).

---

## 2. Setup on Friend's Laptop (Developer)

### Step 1: Clone Repository
```bash
git clone https://github.com/Punith887/docker-auto-login.git
cd docker-auto-login
```

### Step 2: Make Changes & Push
Whenever your friend updates code (e.g., modifying `templates/login.html` or `app.py`):
```bash
git add .
git commit -m "Update login page design"
git push origin main
```

---

## 3. Friend's Browser Access

Make sure both laptops are connected to the same **Wi-Fi / LAN network**.

Open any browser and navigate to:
```
http://192.168.1.55:5000
```

- Login credentials:
  - **Username**: `admin`
  - **Password**: `1234`
- Health check: `http://192.168.1.55:5000/health`
