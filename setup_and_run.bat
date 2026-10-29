@echo off
echo ========================================================
echo   Setting up EduPulse on this computer...
echo ========================================================
echo.
echo Installing Python dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Notice] Trying with 'py' launcher...
    py -m pip install -r requirements.txt
)
echo.
echo ========================================================
echo   Starting EduPulse Academic Monitor & Alarms...
echo ========================================================
python run.py
if %errorlevel% neq 0 (
    py run.py
)
pause
