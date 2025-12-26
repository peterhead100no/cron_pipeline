#!/bin/bash

# Pipeline script to run all data generation scripts sequentially
# This script runs every hour via cron

# Set the working directory
cd "$(dirname "$0")" || exit 1

# Get the Python executable path
PYTHON_EXEC=$(which python3)

# Log file for tracking execution
LOG_FILE="pipeline_execution.log"

# Function to log messages with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Start logging
log_message "========== Pipeline execution started =========="

# Array of scripts to run in sequence
scripts=(
    "exotel_api.py"
    "import_exotel_data.py"
    "get_recording.py"
    "audio_to_text.py"
    "descrption_generation_2.py"
)

# Counter for tracking which script is running
script_count=0
total_scripts=${#scripts[@]}

# Run each script in sequence
for script in "${scripts[@]}"; do
    script_count=$((script_count + 1))
    log_message "[$script_count/$total_scripts] Running $script..."
    
    # Check if script exists
    if [ ! -f "$script" ]; then
        log_message "ERROR: $script not found!"
        continue
    fi
    
    # Run the script and capture exit code
    $PYTHON_EXEC "$script"
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_message "[$script_count/$total_scripts] ✓ $script completed successfully"
    else
        log_message "[$script_count/$total_scripts] ✗ $script failed with exit code $exit_code"
    fi
    
    # Optional: Add a small delay between scripts (in seconds)
    # sleep 5
done

log_message "========== Pipeline execution completed =========="
log_message ""
