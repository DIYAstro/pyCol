@echo off
echo ========================================
echo  pyCol Windows Installer Build Script
echo ========================================

:: Ensure we are running from project root
cd /d "%~dp0\.."

echo.
echo [1/3] Building Executable (Unified Build)...
call scripts\build_win_exe.bat nopause
if errorlevel 1 (
    echo ERROR: EXE build failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Updating Inno Setup script with version...
python scripts\generate_iss.py
if errorlevel 1 (
    echo ERROR: ISS generation failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Building Windows Installer with Inno Setup...
:: Try common Inno Setup paths
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo ERROR: Inno Setup not found! Please install Inno Setup 6.
    pause
    exit /b 1
)

%ISCC% scripts\pyCol.iss
if errorlevel 1 (
    echo ERROR: Inno Setup build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo  BUILD SUCCESSFUL!
echo  Outputs:
echo    - dist\pyCol.exe (Standalone)
echo    - dist\pyCol_Setup_*.exe (Installer)
echo ========================================
pause
