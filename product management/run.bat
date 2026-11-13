@echo off
REM ---------------------------------------------------------------
REM  StockFlow - Inventory & Stock Management System
REM  Double-click this file to start the local development server.
REM ---------------------------------------------------------------
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo Starting StockFlow...
echo Open http://127.0.0.1:5000 in your browser.
echo Press Ctrl+C to stop the server.
echo.

%PYTHON% app.py
pause
