@echo off
setlocal

rem ============================================================
rem  KRUTII TRANS - install and start (Windows)
rem  Backend: Flask (port 5001)
rem  Frontend: Vite (port 5173)
rem  Simulator: optional telematics simulator (own window)
rem ============================================================

rem Move to the script folder so all paths below stay relative
cd /d "%~dp0"

rem This same file is re-opened in a third window for the simulator
if /I "%~1"=="simulator" goto simulator

rem --- Check Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.9+ and add it to PATH.
    pause
    exit /b 1
)

rem --- Check Node.js ---
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js 18+ and add it to PATH.
    pause
    exit /b 1
)

rem ============================================================
rem  MONGODB
rem ============================================================
echo.
echo [0/3] Checking MongoDB...
sc query MongoDB | find "RUNNING" >nul
if errorlevel 1 (
    echo MongoDB is not running, trying to start the service...
    net start MongoDB
    if errorlevel 1 (
        echo [WARN] Could not start the MongoDB service automatically.
        echo        Run this file as Administrator, or start MongoDB manually.
        echo        The backend needs MongoDB on localhost:27017.
        pause
    )
) else (
    echo MongoDB service is already running.
)

rem ============================================================
rem  BACKEND INSTALL
rem ============================================================
echo.
echo [1/3] Backend setup...
cd backend

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Installing Python dependencies...
    call venv\Scripts\python.exe -m pip install --upgrade pip
    call venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install Python dependencies.
        pause
        exit /b 1
    )
    echo Seeding demo data...
    call venv\Scripts\python.exe seed.py
) else (
    echo Checking Python dependencies...
    call venv\Scripts\python.exe -m pip install -q -r requirements.txt
)

cd ..

rem ============================================================
rem  FRONTEND INSTALL
rem ============================================================
echo.
echo [2/3] Frontend setup...
cd frontend

if not exist "node_modules" (
    echo Installing Node.js dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install Node.js dependencies.
        pause
        exit /b 1
    )
) else (
    echo Checking Node.js dependencies...
    call npm install --no-audit --no-fund --loglevel=error
)

cd ..

rem ============================================================
rem  START
rem ============================================================
echo.
echo [3/3] Starting servers...
echo Backend:  http://localhost:5001
echo Frontend: http://localhost:5173
echo.

start "KRUTII TRANS Backend" cmd /k "cd backend && venv\Scripts\python.exe app.py"
start "KRUTII TRANS Frontend" cmd /k "cd frontend && npm run dev"
timeout /t 3 /nobreak >nul
start "KRUTII TRANS Simulator" cmd /c ""%~f0" simulator"

echo Three windows opened: Backend, Frontend and Simulator.
echo In the echo In the Simulator window press 1 to start it, or 2 to close it.
echo Open http://localhost:5173 in your browser.
echo.
echo Note: MongoDB must be running (mongodb://localhost:27017).
pause
endlocal
exit /b 0

rem ============================================================
rem  SIMULATOR WINDOW
rem ============================================================
:simulator
title KRUTII TRANS Simulator
echo ============================================================
echo   Telematics simulator
echo   Fake GPS trackers: cars move on the "Fleet map" page,
echo   sometimes breakdowns and fuel drains happen.
echo ============================================================
echo.
echo   1 - start the simulator
echo   2 - close this window
echo.
choice /C 12 /T 60 /D 2 /N /M "Your choice (1 or 2): "
if errorlevel 2 exit /b 0

echo.
echo Waiting for the backend to start...
timeout /t 8 /nobreak >nul
cd backend
venv\Scripts\python.exe simulator.py
echo.
echo Simulator stopped.
pause
exit /b 0
