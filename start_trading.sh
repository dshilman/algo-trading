#!/bin/bash

# Define array of Forex pairs and strategy identifiers
declare -A forex_pairs
forex_pairs=(
    ["EUR_USD_1"]="MACD"
    ["EUR_GBP_1"]="MACD"
    ["AUD_USD_1"]="MACD"
    ["USD_CAD_1"]="MACD"

    ["EUR_USD_2"]="Mean Reverse"
    ["GBP_USD_2"]="Mean Reverse"
    ["USD_CAD_2"]="Mean Reverse"
    ["AUD_USD_2"]="Mean Reverse"
)

# Loop through each Forex pair and start the trading process if not running
for pair in "${!forex_pairs[@]}"; do
    script="/home/ec2-user/algo-trading/trader_oanda_${pair}.sh"
    log_file="/home/ec2-user/algo-trading/logs/trading/time_check.txt"
    
    if pgrep -f "/bin/sh $script" >/dev/null; then
        echo "$(date) $pair Trading bot is already running."
        echo "$(date) $pair Trading bot is already running." >> $log_file
    else
        echo "$(date) $pair Trading bot is not running. Starting it now..."
        echo "$(date) $pair Trading bot is not running. Starting it now..." >> $log_file
    fi
    $script
done
exit 0