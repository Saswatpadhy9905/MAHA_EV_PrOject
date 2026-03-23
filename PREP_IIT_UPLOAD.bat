@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo Prepare IIT Upload Bundle
echo ========================================
echo.

set DEFAULT_API=/api
set /p API_URL=Enter production API URL [default: /api]: 
if "%API_URL%"=="" set API_URL=%DEFAULT_API%

echo [*] Building frontend with VITE_API_URL=%API_URL%
cd client\Opt-Frontend
call npm install
if errorlevel 1 (
  echo [X] Frontend dependency install failed
  exit /b 1
)

set "VITE_API_URL=%API_URL%"
call npm run build
if errorlevel 1 (
  echo [X] Frontend build failed
  exit /b 1
)
cd ..\..

echo [*] Creating deploy_iit bundle...
if exist deploy_iit rmdir /s /q deploy_iit
mkdir deploy_iit
mkdir deploy_iit\frontend
mkdir deploy_iit\backend

echo [*] Copying frontend build...
xcopy /e /i /y client\Opt-Frontend\dist\* deploy_iit\frontend\ >nul

echo [*] Copying backend runtime files...
copy /y server\server.js deploy_iit\backend\ >nul
copy /y server\package.json deploy_iit\backend\ >nul
if exist server\package-lock.json copy /y server\package-lock.json deploy_iit\backend\ >nul
copy /y requirements.txt deploy_iit\backend\ >nul
copy /y run_simulation.py deploy_iit\backend\ >nul
for %%F in (ev_tc_*.py) do copy /y "%%F" deploy_iit\backend\ >nul

echo [*] Writing backend start helper...
(
echo @echo off
echo setlocal
echo echo Installing backend dependencies...
echo call npm install
echo python -m pip install -r requirements.txt
echo set PORT=5100
echo set NODE_ENV=production
echo node server.js
) > deploy_iit\backend\start_backend_5100.bat

echo.
echo [OK] Bundle ready at: deploy_iit\
echo Upload deploy_iit\frontend to your web root and deploy_iit\backend to server runtime folder.
echo.
endlocal
