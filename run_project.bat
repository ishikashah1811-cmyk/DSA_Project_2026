@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "PYTHON=%PROJECT_ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Python environment not found: "%PYTHON%"
    echo Create the virtual environment and install backend\requirements.txt first.
    pause
    exit /b 1
)

if not exist "%PROJECT_ROOT%Dataset\instagram_posts_synthetic.csv" (
    echo Dataset not found: "%PROJECT_ROOT%Dataset\instagram_posts_synthetic.csv"
    pause
    exit /b 1
)

if not exist "%PROJECT_ROOT%frontend\node_modules\.bin\next.cmd" (
    echo Frontend dependencies not found.
    echo Run "npm install" in the frontend folder first.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo npm was not found. Install Node.js and ensure npm is on PATH.
    pause
    exit /b 1
)

start "ContentIQ Backend" /D "%PROJECT_ROOT%backend" "%PYTHON%" -m uvicorn app.main:app --reload
start "ContentIQ Frontend" /D "%PROJECT_ROOT%frontend" cmd /k "npm run dev"

echo ContentIQ is starting.
echo Frontend: http://localhost:3000
echo Backend API: http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
echo Keep both terminal windows open while using the app.

timeout /t 5 /nobreak >nul
start "" "http://localhost:3000"
