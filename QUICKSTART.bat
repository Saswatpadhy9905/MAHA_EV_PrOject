@echo off
REM Quick Start Script for EV Charging Station Simulation (Windows)

echo.
echo ================================
echo EV Charging Simulation - Quick Start
echo ================================
echo.

REM Check if Node.js is installed
where /q node
if errorlevel 1 (
    echo [X] Node.js not found. Please install Node.js first.
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js found: %NODE_VERSION%

REM Check if Python is installed
where /q python
if errorlevel 1 (
    echo [X] Python not found. Please install Python first.
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Python found: %PYTHON_VERSION%

REM Install backend dependencies
echo.
echo [*] Installing backend dependencies...
cd server
call npm install
cd ..

REM Install frontend dependencies
echo [*] Installing frontend dependencies...
cd client\Opt-Frontend
call npm install
cd ..\..

REM Check Python dependencies
echo [*] Checking Python dependencies...
python -c "import networkx, numpy, matplotlib, scipy; print('[OK] All Python dependencies found')" 2>nul || (
    echo [!] Installing Python dependencies...
    pip install networkx numpy matplotlib scipy
)

echo.
echo ================================
echo [OK] Setup Complete!
echo ================================
echo.
echo To start the application:
echo.
echo Terminal 1 - Start Backend:
echo   cd server
echo   npm start
echo.
echo Terminal 2 - Start Frontend:
echo   cd client\Opt-Frontend
echo   npm run dev
echo.
echo Then open http://localhost:5173 in your browser
echo.
pause
