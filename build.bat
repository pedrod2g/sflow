@echo off
echo Building SFlow for Windows...

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Install dependencies
echo Installing dependencies...
python -m pip install -r requirements.txt

:: Install pyinstaller if missing
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)

:: Clean previous builds
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

:: Build with PyInstaller
echo Running PyInstaller...
python -m PyInstaller --clean sflow_win.spec

echo.
echo Build complete! The executable is located in the dist\SFlow folder.
echo You can run it directly from dist\SFlow\SFlow.exe.
pause
