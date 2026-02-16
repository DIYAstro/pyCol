@echo off
echo ========================================
echo  pyCol Build Script (Unified)
echo ========================================

:: Ensure we are running from project root
cd /d "%~dp0\.."

echo.
echo.
echo [1/5] Cleaning previous builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo.
echo [2/5] Generating version files from versioninfo.json...
python scripts\generate_version.py
if errorlevel 1 (
    echo ERROR: Version generation failed!
    pause
    exit /b 1
)

echo.
echo [3/5] Generating Icon...
python scripts\generate_icon.py
if errorlevel 1 (
    echo ERROR: Icon generation failed!
    pause
    exit /b 1
)

echo.
echo [4/5] Installing dependencies...
pip install pyinstaller Pillow --quiet

echo.
echo [5/5] Reading Plugin Configuration...
set /p PLUGIN_ARGS=<build\pyinstaller_args.txt
echo Plugins: %PLUGIN_ARGS%

echo.
echo [6/6] Building Executable...
del /q *.spec 2>nul

python -m PyInstaller ^
    --noconsole ^
    --onefile ^
    --clean ^
    --name "pyCol" ^
    --icon="build/icon.ico" ^
    --version-file="build/version_info.txt" ^
    --add-data "src/icon.png;." ^
    %PLUGIN_ARGS% ^
    src/main.py

if errorlevel 1 (
    echo.
    echo BUILD FAILED!
    if "%1"=="nopause" exit /b 1
    pause
    exit /b 1
)

echo.
echo ========================================
echo  BUILD SUCCESSFUL!
echo  Output: dist\pyCol.exe
echo ========================================

if "%1"=="nopause" exit /b 0
pause
