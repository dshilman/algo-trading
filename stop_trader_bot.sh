#!/bin/bash

# Function to check if a process is running by name
check_process() {
    local process_name="$1"
    # Check if the process exists
    if pgrep -f "$process_name" >/dev/null; then
        return 0  # Process is running
    else
        return 1  # Process is not running
    fi
}

# Main script
if [ $# -ne 1 ]; then
    echo "Usage: $0 <process_name>"
    exit 1
fi

process_name="$1"

if check_process "$process_name"; then
    echo "Process $process_name is running. Attempting to kill..."
    pkill -f "$process_name"
    if [ $? -eq 0 ]; then
        echo "Process $process_name killed successfully."
    else
        echo "Failed to kill process $process_name."
        exit 1
    fi
else
    echo "Process $process_name is not running."
    exit 1
fi

exit 0
