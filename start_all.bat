@echo off
:menu
cls
echo ==========================================
echo    UIDAI Server Manager
echo ==========================================
echo [S] Start Servers
echo [K] Kill Servers
echo [E] Exit Manager
echo.
choice /c SKE /n /m "Select an option (S/K/E): "

if errorlevel 3 goto eof
if errorlevel 2 goto stop
if errorlevel 1 goto start

:start
echo.
echo Terminating any existing server windows...
taskkill /FI "WINDOWTITLE eq Backend" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend" /F /T >nul 2>&1

start "Backend" cmd /c start_backend.bat
start "Frontend" cmd /c start_frontend.bat

echo.
echo Servers launched in separate windows!
echo ==========================================
echo Quick Actions:
echo [R] Restart both servers (Refreshes code)
echo [E] Stop servers and Exit Manager
echo ==========================================
choice /c RE /n /m "Press a key: "
if errorlevel 2 goto stop_and_exit
if errorlevel 1 goto start

:stop
echo.
echo [1/2] Terminating server windows...
taskkill /FI "WINDOWTITLE eq Backend" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend" /F /T >nul 2>&1

echo [2/2] Cleaning up lingering processes on ports 8000 and 8050...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    if not "%%a"=="0" taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8050') do (
    if not "%%a"=="0" taskkill /F /PID %%a >nul 2>&1
)

echo All servers successfully stopped!
echo.
echo [M] Return to Main Menu
echo [E] Exit Manager
choice /c ME /n /m "Press a key: "
if errorlevel 2 goto eof
if errorlevel 1 goto menu

:stop_and_exit
echo.
echo [1/2] Terminating server windows...
taskkill /FI "WINDOWTITLE eq Backend" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend" /F /T >nul 2>&1

echo [2/2] Cleaning up lingering processes on ports 8000 and 8050...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    if not "%%a"=="0" taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8050') do (
    if not "%%a"=="0" taskkill /F /PID %%a >nul 2>&1
)
goto eof

:eof
