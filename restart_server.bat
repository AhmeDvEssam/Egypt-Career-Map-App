@echo off
REM Kill any existing Python processes
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak

REM Start the Dash server
cd /d "d:\Hire Q Project\Modeling _2"
python DashApp.py
pause
