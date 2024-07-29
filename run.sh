#!/bin/bash

echo "The script you are running has:"
echo "basename: [$(basename "$0")]"
echo "dirname : [$(dirname "$0")]"
echo "pwd     : [$(pwd)]"

DIRNAME="$(dirname "$0")"
APPLICATION="dashboard.py"

cd $DIRNAME

# Check if the provided Python application file exists
if [ ! -f "$APPLICATION" ]; then
    echo "The specified Python application file '$APPLICATION' does not exist."
    exit 0
fi

# Check if requirements.txt file exists
if [ ! -f "requirements.txt" ]; then
    echo "requirements.txt file not found in the current directory."
    exit 0
fi

# Create a virtual environment if it does not exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install the required packages
echo "Installing required packages..."
pip install -r requirements.txt

# Run the Python application
echo "Running application $APPLICATION..."
python3 $APPLICATION

# Deactivate the virtual environment after finishing
echo "Deactivate the virtual environment"
deactivate

echo 0
