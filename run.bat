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
    echo Syncing dependencies using uv...
    uv lock
    uv sync
) else (
    if not exist ".venv" (
        echo Creating virtual environment using python venv...
        python -m venv .venv
    )
    echo Syncing dependencies using pip...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\pip install -r requirements.txt
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

