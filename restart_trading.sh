#!/bin/bash

# Check if stop_trading.sh exists and is executable
if [ ! -x stop_trading.sh ]; then
    echo "$(date) "stop_trading.sh script not found or not executable."
    exit 1
fi

# Check if start_trading.sh exists and is executable
if [ ! -x start_trading.sh ]; then
    echo "$(date) "start_trading.sh script not found or not executable."
    exit 1
fi

echo "$(date) "Stopping trading..."
./stop_trading.sh
if [ $? -eq 0 ]; then
    echo "$(date) "Trading stopped successfully."
else
    echo "$(date) "Failed to stop trading."
fi

echo "$(date) "Starting trading..."

./start_trading.sh
if [ $? -eq 0 ]; then
    echo "$(date) "Trading started successfully."
else
    echo "$(date) "Failed to start trading."
    exit 1
fi
exit 0
