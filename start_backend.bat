@echo off
echo ==========================================
echo    Starting FastAPI Backend
echo ==========================================

echo [1/2] Checking if port 8000 is in use...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    if not "%%a"=="0" (
        echo Killing process %%a on port 8000...
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo [2/2] Syncing dependencies and starting server...
uv sync
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
