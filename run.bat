@echo off
echo ==========================================
echo    Starting Application Setup
echo ==========================================

echo.
echo [1/3] Checking virtual environment and syncing dependencies...
where uv >nul 2>nul
if %errorlevel% equ 0 (
    if not exist ".venv" (
        echo Creating virtual environment using uv...
        uv venv
    )
    echo Adding additionl dependencies
    uv add -r requirements.txt
    echo Syncing dependencies using uv...
    uv sync
    uv lock
) else (
    if not exist ".venv" (
        echo Creating virtual environment using python venv
        pip install uv
        uv venv .venv
    )
    echo Syncing dependencies using uv...
    uv pip install --upgrade pip
    uv add -r requirements.txt
    uv sync
    uv lock
)

echo.
echo [2/3] Processing raw data...
.venv\Scripts\python.exe backend\preprocess.py
if errorlevel 1 (
    echo Error during data processing. Please check the logs above.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Starting the Servers...
echo Starting FastAPI Backend API...
start cmd /k ".venv\Scripts\uvicorn.exe backend.api.main:app --host 127.0.0.1 --port 8000"

echo Starting Dash Frontend...
echo The application will be available at http://127.0.0.1:8050
cd frontend && ..\.venv\Scripts\python.exe app.py
if errorlevel 1 (
    echo Error starting the frontend application. Please check the logs above.
    pause
    exit /b %errorlevel%
)

pause
