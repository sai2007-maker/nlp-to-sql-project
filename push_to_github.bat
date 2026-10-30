@echo off
title Push Project to GitHub
color 0A
echo ========================================================
echo         DMAI NLP-to-Database - GitHub Pusher
echo ========================================================
echo.

set "GIT_EXE=C:\Users\saisu\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd\git.exe"
if not exist "%GIT_EXE%" (
    set "GIT_EXE=git"
)

cd /d "%~dp0"

echo [1/4] Checking Git repository status...
"%GIT_EXE%" status >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    "%GIT_EXE%" init -b main
    "%GIT_EXE%" config user.name "saisu"
    "%GIT_EXE%" config user.email "saisu@example.com"
)

echo [2/4] Staging and committing all files...
"%GIT_EXE%" add .
"%GIT_EXE%" commit -m "Update project files" >nul 2>&1

echo [3/4] Checking remote origin...
"%GIT_EXE%" remote get-url origin >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Please enter your GitHub repository URL:
    echo (e.g. https://github.com/your-username/dmai-nlp-database.git)
    set /p REPO_URL="Repository URL: "
    if "%REPO_URL%"=="" (
        color 0C
        echo [ERROR] No URL provided. Aborting.
        pause
        exit /b 1
    )
    "%GIT_EXE%" remote add origin "%REPO_URL%"
)

echo [4/4] Pushing to main branch...
"%GIT_EXE%" branch -M main
"%GIT_EXE%" push -u origin main

if %ERRORLEVEL% EQU 0 (
    color 0A
    echo.
    echo ========================================================
    echo   SUCCESS! All project files pushed to GitHub.
    echo ========================================================
) else (
    color 0C
    echo.
    echo ========================================================
    echo   [ERROR] Push failed. Please check your repository URL
    echo   and ensure you are signed in or have write permissions.
    echo ========================================================
)
pause
