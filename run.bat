@echo off
title MatchaIn GC - RUN

echo [INFO] Mengaktifkan virtual environment...
call .venv\Scripts\activate

echo [INFO] Menjalankan aplikasi...
echo ===================================================
echo.
python main.py

echo.
echo ===================================================
echo   Aplikasi berhenti.
pause
