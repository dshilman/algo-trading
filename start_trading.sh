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

echo "Current directory: $(pwd)"
# Navigate to the algo-trading directory (absolute path recommended)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Targrt directory: $(SCRIPT_DIR)/trading"
cd "$SCRIPT_DIR/algo-trading" || { echo "Directory algo-trading not found"; exit 1; }

# Loop through each Forex pair and start the trading process if not running
for pair in "${!forex_pairs[@]}"; do
    script="./trader_oanda_${pair}.sh"
    log_file="logs/trading/time_check.txt"
    
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