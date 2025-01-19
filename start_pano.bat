@echo off
setlocal EnableDelayedExpansion

:: Colors for output
set "BLUE=[94m"
set "GREEN=[92m"
set "NC=[0m"

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.x from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo %BLUE%Starting PANO setup...%NC%

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo %BLUE%Creating virtual environment...%NC%
    python -m venv venv
)

:: Activate virtual environment
echo %BLUE%Activating virtual environment...%NC%
call venv\Scripts\activate.bat

:: Install requirements if requirements.txt exists
if exist "requirements.txt" (
    echo %BLUE%Installing/updating dependencies...%NC%
    pip install -r requirements.txt
) else (
    echo %BLUE%Installing required packages...%NC%
    pip install PySide6 ^
    networkx ^
    qasync ^
    scipy ^
    folium ^
    aiofiles ^
    requests ^
    bs4 ^
    googlesearch-python ^
    geopy ^
    ghunt ^
    googletrans ^
    markdown2 ^
    g4f
)

:: Always update g4f to latest version
pip uninstall -y g4f
pip install --no-cache-dir g4f

:: Start PANO
echo %GREEN%Starting PANO...%NC%
python pano.py

pause 