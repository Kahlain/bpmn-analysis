#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies if needed
pip install -r requirements.txt

# Run the Streamlit app
streamlit run bpmn_analyzer.py

echo "Development environment activated and app started!"
