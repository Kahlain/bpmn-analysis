#!/bin/bash

echo "🚀 Starting BPMN Business Analysis Tool..."
echo "=================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "bpmn_analyzer.py" ]; then
    echo "❌ Error: bpmn_analyzer.py not found!"
    echo "Please run this script from the project directory."
    exit 1
fi

# Install dependencies
echo "🔍 Installing dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Launch the application
echo "🌐 Launching BPMN Analysis Tool..."
echo "The application will open in your default web browser."
echo "If it doesn't open automatically, navigate to: http://localhost:8501"
echo "=================================================="

streamlit run bpmn_analyzer.py
