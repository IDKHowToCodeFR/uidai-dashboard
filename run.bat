@echo off
echo ==========================================
echo    Starting PostHog Dashboard Setup
echo ==========================================

echo.
echo [1/3] Syncing dependencies...
uv pip install -r requirements.txt

echo.
echo [2/3] Processing raw data...
.venv\Scripts\python.exe backend\preprocess.py
if errorlevel 1 (
    echo Error during data processing. Please check the logs above.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Starting the Dashboard Server...
echo The dashboard will be available at http://127.0.0.1:8050
.venv\Scripts\python.exe frontend\app.py
if errorlevel 1 (
    echo Error starting the dashboard. Please check the logs above.
    pause
    exit /b %errorlevel%
)

pause
