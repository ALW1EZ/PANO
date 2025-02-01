@echo off
echo Checking PANO version...

REM Check if git is installed
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Git is not installed. Please install git first.
    pause
    exit /b 1
)

REM Check if we're in a git repository
git rev-parse --is-inside-work-tree >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Not in a git repository. Please clone PANO properly.
    pause
    exit /b 1
)

REM Make sure we're on main branch
for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD') do set CURRENT_BRANCH=%%a
if not "%CURRENT_BRANCH%" == "main" (
    echo Switching to main branch...
    git checkout main
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to switch to main branch. Please check your git status.
        pause
        exit /b 1
    )
)

REM Fetch the latest changes without merging
git fetch origin main

REM Get current and latest versions
for /f "tokens=*" %%a in ('git rev-parse HEAD') do set CURRENT_VERSION=%%a
for /f "tokens=*" %%a in ('git rev-parse origin/main') do set LATEST_VERSION=%%a

if not "%CURRENT_VERSION%" == "%LATEST_VERSION%" (
    echo Your PANO version is outdated.
    echo Current version: %CURRENT_VERSION:~0,7%
    echo Latest version: %LATEST_VERSION:~0,7%
    set /p UPDATE="Would you like to update? [y/N] "
    if /i "%UPDATE%" == "y" (
        echo Updating PANO...
        git pull origin main
        if %ERRORLEVEL% NEQ 0 (
            echo Update failed. Please resolve any conflicts and try again.
            pause
            exit /b 1
        )
        echo Update successful!
    ) else (
        echo Continuing with current version...
    )
) else (
    echo PANO is up to date.
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
) else (
    call venv\Scripts\activate
)

echo Installing dependencies...
pip install -r requirements.txt

REM updating g4f
pip install -U g4f

REM Start PANO
echo Starting PANO...
python pano.py
pause 