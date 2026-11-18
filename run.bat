@echo off
setlocal enabledelayedexpansion
title Academic Timetable Scheduler

:: Change working directory to the folder containing this batch script
cd /d "%~dp0"

echo ======================================================================
echo          Constraint-Based Academic Timetable Scheduler
echo ======================================================================
echo.

:: Detect Python executable
set "PYTHON_CMD="
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_CMD=py"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check if required dependencies are installed
echo [*] Checking required dependencies...
"%PYTHON_CMD%" -c "import flask, openpyxl" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Installing dependencies from requirements.txt...
    "%PYTHON_CMD%" -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install requirements. Please check your internet connection.
        pause
        exit /b 1
    )
)

echo [*] Starting Timetable Scheduler server...
echo [*] Opening your browser at http://127.0.0.1:5001 ...
echo.
echo ======================================================================
echo  App is RUNNING!
echo  To stop the server, press Ctrl+C or simply close this window.
echo ======================================================================
echo.

"%PYTHON_CMD%" app.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [Server exited with code %ERRORLEVEL%]
    pause
)
