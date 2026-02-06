#!/bin/bash

# Define array of Forex pairs and strategy identifiers
declare -A forex_pairs
forex_pairs=(
    ["EUR_USD_1"]="MACD"
    # ["EUR_GBP_1"]="MACD"
    # ["AUD_USD_1"]="MACD"
    # ["USD_CAD_1"]="MACD"

    ["EUR_USD_2"]="Mean Reverse"
    # ["GBP_USD_2"]="Mean Reverse"
    # ["USD_CAD_2"]="Mean Reverse"
    # ["AUD_USD_2"]="Mean Reverse"
)

echo "$(date) Current directory: $(pwd)"

# Loop through each Forex pair and start the trading process if not running
for pair in "${!forex_pairs[@]}"; do
    script="trader_oanda_${pair}.sh"
    
    if pgrep -f "/bin/sh ./$script" >/dev/null; then
        echo "$(date) $script Trading bot is already running."
    else
        echo "$(date) $script Trading bot is not running. Starting it now..."

        if [ ! -x $script ]; then
            echo "$(date) $script script not found or not executable."
            exit 1
        fi

        ./$script&
    fi


done
exit 0