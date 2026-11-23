@echo off
setlocal

rem ============================================================
rem  KRUTII TRANS - install and start (Windows)
rem  Backend: Flask (port 5001)
rem  Frontend: Vite (port 5173)
rem ============================================================

rem Move to the script folder so all paths below stay relative
cd /d "%~dp0"

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
    echo Virtual environment already exists, skipping install.
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
    echo node_modules already exists, skipping install.
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

start "KRUTII TRANS Backend" cmd /k "cd backend && call venv\Scripts\activate && python app.py"
start "KRUTII TRANS Frontend" cmd /k "cd frontend && npm run dev"

echo Two windows opened (Backend and Frontend).
echo Open http://localhost:5173 in your browser.
echo.
echo Note: MongoDB must be running (mongodb://localhost:27017).
pause
endlocal
