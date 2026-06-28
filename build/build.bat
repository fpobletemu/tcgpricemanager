@echo off
:: ============================================================
:: TCG Price Manager — Build Script
:: Generates dist\TCG Price Manager.exe
:: Run from the project root: build\build.bat
:: ============================================================

setlocal
cd /d %~dp0..

echo.
echo ====================================================
echo  TCG Price Manager — Build EXE
echo ====================================================
echo.

:: Activate venv
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Virtual environment not found.
    echo Run first: python -m venv .venv and install requirements.txt
    pause & exit /b 1
)

:: Generate icon if missing
if not exist "tcg_app\assets\icon.ico" (
    echo Generating icon...
    python generate_icon.py
)

:: Install pyinstaller if missing
python -c "import PyInstaller" 2>nul || (
    echo Installing PyInstaller...
    pip install pyinstaller -q
)

:: Clean previous build
if exist "dist\TCG Price Manager.exe" del /f /q "dist\TCG Price Manager.exe"

:: Build
echo.
echo Building EXE...
echo.
pyinstaller build\TCGPriceManager.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo BUILD FAILED — see errors above.
    pause & exit /b 1
)

echo.
echo ====================================================
echo  BUILD COMPLETE
echo  Output: dist\TCG Price Manager.exe
echo ====================================================
echo.

:: Ask to create shortcut to the EXE
set /p SHORTCUT="Create desktop shortcut? (y/n): "
if /i "%SHORTCUT%"=="y" (
    python setup_shortcut.py --exe "dist\TCG Price Manager.exe"
)

pause
