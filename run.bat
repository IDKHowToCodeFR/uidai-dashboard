@echo off
echo ==========================================
echo    Starting Application Setup
echo ==========================================

echo.
echo [1/3] Checking virtual environment and syncing dependencies...
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo uv not found. Installing uv using pip...
    pip install uv
)

if not exist ".venv" (
    echo Creating virtual environment using uv...
    uv venv
)

echo Syncing dependencies exactly from requirements.txt...
uv pip install -r requirements.txt
uv sync 
uv lock
if errorlevel 1 (
    echo [!] uv pip install failed. Falling back to standard pip install...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo.
echo [2/3] Processing raw data...
.venv\Scripts\python.exe backend\data_ingestion\preprocess.py
if errorlevel 1 (
    echo Error during data processing. Please check the logs above.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Starting the Servers...
echo import subprocess, sys, time > .tmp_runner.py
echo print("Starting FastAPI Backend on port 8000...") >> .tmp_runner.py
echo backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"]) >> .tmp_runner.py
echo time.sleep(1) >> .tmp_runner.py
echo print("Starting Dash Frontend on port 8050...") >> .tmp_runner.py
echo frontend = subprocess.Popen([sys.executable, "-m", "frontend.app"]) >> .tmp_runner.py
echo try: >> .tmp_runner.py
echo     while backend.poll() is None and frontend.poll() is None: >> .tmp_runner.py
echo         time.sleep(1) >> .tmp_runner.py
echo     print("\n[!] One of the servers stopped. Shutting down...") >> .tmp_runner.py
echo except: >> .tmp_runner.py
echo     print("\n[!] Shutting down servers...") >> .tmp_runner.py
echo backend.terminate() >> .tmp_runner.py
echo frontend.terminate() >> .tmp_runner.py

.venv\Scripts\python.exe .tmp_runner.py
del .tmp_runner.py

if errorlevel 1 (
    echo Error starting the servers. Please check the logs above.
    pause
    exit /b %errorlevel%
)

pause
