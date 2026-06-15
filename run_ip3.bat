@echo off
chcp 65001 >nul
title IP3
cd /d "%~dp0"

REM Pick a Python launcher: prefer "py", fall back to "python".
set "PYEXE=python"
where py >nul 2>nul && set "PYEXE=py"

REM First run: install dependencies if Streamlit is missing.
%PYEXE% -c "import streamlit" 1>nul 2>nul
if errorlevel 1 (
    echo [IP3] Installing required packages. This may take a few minutes...
    %PYEXE% -m pip install -r requirements.txt
)

echo [IP3] Starting IP3. Your browser will open automatically.
start "" /MIN cmd /C "timeout /t 3 /nobreak >nul && start http://localhost:8501"
%PYEXE% -m streamlit run app.py --server.port 8501 --server.headless false
pause
