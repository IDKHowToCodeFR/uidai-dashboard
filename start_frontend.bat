@echo off
echo ==========================================
echo    Starting Dash Frontend
echo ==========================================

echo [1/2] Checking if port 8050 is in use...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8050') do (
    if not "%%a"=="0" (
        echo Killing process %%a on port 8050...
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo [2/2] Syncing dependencies and starting server...
uv sync
uv run python -m frontend.app
pause
