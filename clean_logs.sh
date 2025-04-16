#!/bin/bash

# Set the directory containing the log files
LOG_DIR="logs/trading/"

echo "Starting log cleanup..."

# Find and delete .log files older than 1 day, printing each one
find "$LOG_DIR" -type f -name "*.log*" -mtime +0 | while read -r file; do
    echo "Deleting: $file"
    rm -f "$file"
done

echo "Log cleanup completed."