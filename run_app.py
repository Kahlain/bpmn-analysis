#!/usr/bin/env python3
"""
Simple startup script for the BPMN Business Analysis Tool.
This script checks dependencies and launches the Streamlit application.
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'streamlit',
        'xmltodict', 
        'pandas',
        'plotly',
        'numpy',
        'openpyxl'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies():
    """Install missing dependencies."""
    print("Installing missing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies. Please install manually:")
        print("pip install -r requirements.txt")
        return False

def main():
    """Main startup function."""
    print("🚀 Starting BPMN Business Analysis Tool...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("bpmn_analyzer.py"):
        print("❌ Error: bpmn_analyzer.py not found!")
        print("Please run this script from the project directory.")
        sys.exit(1)
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("Installing dependencies...")
        if not install_dependencies():
            sys.exit(1)
    else:
        print("✅ All dependencies are installed!")
    
    # Launch the application
    print("🌐 Launching BPMN Analysis Tool...")
    print("The application will open in your default web browser.")
    print("If it doesn't open automatically, navigate to: http://localhost:8501")
    print("=" * 50)
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "bpmn_analyzer.py"])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user.")
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        print("Try running manually: streamlit run bpmn_analyzer.py")

if __name__ == "__main__":
    main()
