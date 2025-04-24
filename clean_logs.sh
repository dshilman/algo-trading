#!/bin/bash

# Get script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set the log directory relative to script location
LOG_DIR="$SCRIPT_DIR/logs/trading"

echo "Starting log cleanup in $LOG_DIR..."

# Find and delete .log files older than 1 day, printing each one
find "$LOG_DIR" -type f -mmin +1440 | while read -r file; do
    echo "Deleting: $file"
    rm -f "$file"
done

echo "Log cleanup completed."
