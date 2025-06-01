#!/bin/bash
set -e

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

echo "Python environment setup complete."
echo "To activate your environment, run: source .venv/bin/activate"
echo "To run the process monitor, use: python process_monitor_mqtt.py"
