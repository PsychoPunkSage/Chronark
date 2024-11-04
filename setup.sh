#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Navigate to the project directory relative to the script location
PROJECT_DIR="$(dirname "$SCRIPT_DIR")/Bank-sys/src/api"

# Check if the project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory $PROJECT_DIR does not exist."
    exit 1
fi

# Navigate to the project directory
cd "$PROJECT_DIR" || { echo "Failed to navigate to project directory: $PROJECT_DIR"; exit 1; }

# Run the Python script
python3 post.py

# Check if the Python script ran successfully
if [ $? -eq 0 ]; then
    echo "Python script executed successfully."
    echo ""
    echo "================================="
    echo "|| Visit: http://localhost:80/ ||"
    echo "================================="

    echo "Note: Visit ./src/api to get an idea of structure of API calls."
else
    echo "Python script execution failed."
fi
