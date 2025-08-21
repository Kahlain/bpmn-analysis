@echo off
echo 🚀 Starting BPMN Business Analysis Tool...
echo ==================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "bpmn_analyzer.py" (
    echo ❌ Error: bpmn_analyzer.py not found!
    echo Please run this script from the project directory.
    pause
    exit /b 1
)

REM Install dependencies
echo 🔍 Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

REM Launch the application
echo 🌐 Launching BPMN Analysis Tool...
echo The application will open in your default web browser.
echo If it doesn't open automatically, navigate to: http://localhost:8501
echo ==================================================

streamlit run bpmn_analyzer.py

pause
