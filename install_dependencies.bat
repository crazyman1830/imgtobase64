@echo off
echo Installing Image Base64 Converter dependencies...
echo.
echo Checking Python installation...
python --version
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.6 or higher from https://python.org
    pause
    exit /b 1
)
echo.
echo Installing required packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)
echo.
echo Installation completed successfully!
echo You can now run:
echo   - run_web.bat (for web interface)
echo   - run_cli.bat (for command line interface)
echo.
pause