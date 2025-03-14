#!/bin/bash

# Define array of Forex pairs
forex_pairs=(
    "EUR_USD"
    "EUR_GBP"
    "AUD_USD"
    "GBP_USD"
    "USD_CAD"
)

# Loop through each Forex pair and stop related processes
for pair in "${forex_pairs[@]}"; do
    echo "$(date) Stopping processes for $pair..."
    pkill -f "/bin/sh ./trader_oanda_${pair}_*.sh"
    pkill -f "python3 code/trading/trading_bot.py ${pair}#*"
done
exit 0