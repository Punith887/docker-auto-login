@echo off
title Docker Auto-Deploy (Webhook + Watcher)
cd /d "%~dp0"
echo Starting GitHub Webhook listener and Watcher...
python auto_sync.py
pause
