@echo off
title Docker Auto-Sync & Deploy
cd /d "%~dp0"
echo Starting Docker Auto-Sync...
python auto_sync.py
pause
