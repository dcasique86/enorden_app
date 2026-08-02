@echo off
cd /d "%~dp0"
start /b "" "venv\Scripts\python.exe" -m uvicorn main:app --port 8000 --log-level warning
