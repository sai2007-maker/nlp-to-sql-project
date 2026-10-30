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

echo [1/4] Ensuring Git repository is ready...
"%GIT_EXE%" status >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    "%GIT_EXE%" init -b main
    "%GIT_EXE%" config user.name "sai2007-maker"
    "%GIT_EXE%" config user.email "sai2007-maker@users.noreply.github.com"
)

echo [2/4] Staging and committing all project files...
"%GIT_EXE%" add .
"%GIT_EXE%" commit -m "DMAI NLP to Database project with flexible query parser and web UI" >nul 2>&1

echo [3/4] Configuring remote repository...
set "REPO_URL=https://github.com/sai2007-maker/nlp-to-sql-project.git"
"%GIT_EXE%" remote remove origin >nul 2>&1
"%GIT_EXE%" remote add origin %REPO_URL%
echo Remote set to: %REPO_URL%

echo.
echo [4/4] Pushing files to GitHub (main branch)...
echo If prompted, please complete the GitHub sign-in in your browser window.
echo --------------------------------------------------------
"%GIT_EXE%" branch -M main
"%GIT_EXE%" push -u origin main

if %ERRORLEVEL% EQU 0 (
    color 0A
    echo.
    echo ========================================================
    echo   SUCCESS! All project files are pushed to GitHub:
    echo   %REPO_URL%
    echo ========================================================
) else (
    color 0C
    echo.
    echo ========================================================
    echo   [ERROR] Push failed. 
    echo   If this is a private repo or requires a token, you can
    echo   paste a GitHub Personal Access Token when prompted.
    echo ========================================================
)
echo.
pause
