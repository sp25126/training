@echo off
echo Building Training QA Generator EXE...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements_exe.txt

REM Install auto-py-to-exe if not already installed
pip install auto-py-to-exe pyinstaller

REM Create the EXE using the configuration file
echo.
echo Building EXE file...
auto-py-to-exe --config build_config.json --output-dir ./dist

REM Check if build was successful
if exist "dist\gui_app.exe" (
    echo.
    echo ✅ Build successful!
    echo EXE file location: dist\gui_app.exe
    echo.
    echo You can now run the application by double-clicking gui_app.exe
    echo.
) else (
    echo.
    echo ❌ Build failed. Check the output above for errors.
    echo.
)

pause
