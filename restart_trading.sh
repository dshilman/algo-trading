#!/bin/bash

# Check if stop_trading.sh exists and is executable
if [ ! -x stop_trading.sh ]; then
    echo "stop_trading.sh script not found or not executable."
    exit 1
fi

# Check if start_trading.sh exists and is executable
if [ ! -x start_trading.sh ]; then
    echo "start_trading.sh script not found or not executable."
    exit 1
fi

echo "Stopping trading..."
./stop_trading.sh

if [ $? -eq 0 ]; then
    echo "Trading stopped successfully."
else
    echo "Failed to stop trading."
fi

echo "Starting trading..."

./start_trading.sh
if [ $? -eq 0 ]; then
    echo "Trading started successfully."
else
    echo "Failed to start trading."
    exit 1
fi
exit 0
