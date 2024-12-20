#!/bin/bash

# Define array of process names
processes=(
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_1.sh"
    "python3 trading_bot.py EUR_USD#1"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_2.sh"
    "python3 trading_bot.py EUR_USD#2"
    # "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_GBP.sh"
    # "python3 trading_bot.py EUR_GBP"
    # "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_GBP.sh"
    # "python3 trading_bot.py EUR_GBP"
    # "/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_USD.sh"
    # "python3 trading_bot.py GBP_USD"
   )

# Loop through each process name
for process_name in "${processes[@]}"; do
    echo "Stopping $process_name process..."
    pkill -f "$process_name"
done
