@echo off
title DMAI NLP Web Server Controller
color 0A
echo ========================================================
echo   DMAI NLP-to-Database Web Server - Quick Restarter
echo ========================================================
echo.
echo [1/3] Freeing port 8000 (closing any existing server)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo       Stopping previous process PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo [2/3] Opening web browser at http://localhost:8000 ...
cd /d "C:\Users\saisu\OneDrive\Desktop\dmai_nlp_database"
start "" "http://localhost:8000"

echo [3/3] Launching Web Server...
echo ========================================================
echo Server running at http://localhost:8000
echo Press Ctrl+C in this window to stop the server anytime.
echo ========================================================
python main.py --web --port 8000
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [ERROR] Server stopped with error code %ERRORLEVEL%.
    pause
)
