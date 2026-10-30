@echo off
title DMAI NLP-to-SQL Web Server
cd /d "%~dp0"
echo ========================================================
echo  Starting DMAI NLP-to-SQL Web Server on port 8000...
echo ========================================================
echo.
start http://localhost:8000
python main.py --web --port 8000
pause
