#!/bin/bash

# Set the directory containing the log files
LOG_DIR="/logs/trading"

# Find and delete .log files older than 1 day
find "$LOG_DIR" -type f -name "*.log" -mtime +1 -exec rm -f {} \;

echo "Log cleanup completed."
