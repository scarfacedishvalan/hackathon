@echo off
echo Launching Hackathon Full Stack Environment...

REM ---------- Add NodeJS ----------
set PATH="C:\Program Files\nodejs";%PATH%

REM ---------- Start Backend ----------
start cmd /k "call C:\Python\hackathon\.venv\Scripts\activate.bat && cd /d C:\Python\hackathon\backend && uvicorn app.main:app --reload --port 8000"

REM Wait for backend to initialize
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM ---------- Start Frontend ----------
start cmd /k "set PATH=C:\Program Files\nodejs;%PATH% && cd /d C:\Python\hackathon\frontend\port_optim && npm run dev"

echo.
echo Backend and Frontend launched.
pause