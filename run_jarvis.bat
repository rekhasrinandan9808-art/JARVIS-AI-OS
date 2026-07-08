@echo off
title JARVIS AI OS
echo ========================================
echo         JARVIS AI OS Launcher
echo ========================================
echo.

:: Set Python path
set PYTHONPATH=%CD%

:: Run JARVIS
python run_jarvis.py

if errorlevel 1 (
    echo.
    echo ⚠️ JARVIS exited with an error.
    pause
)