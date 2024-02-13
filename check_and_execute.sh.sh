#!/bin/bash

# Check if "abc" script is running
if pgrep -x "./trader_oanda_EUR_HKD.sh" > /dev/null
then
    echo "The './trader_oanda_EUR_HKD.sh' script is already running."
else
    echo "The './trader_oanda_EUR_HKD.sh' script is not running. Starting it now..."
    # Replace the command below with the actual command to execute the "abc" script
    # ./trader_oanda_EUR_HKD.sh &  # Modify this line according to the location and name of your "abc" script
fi
