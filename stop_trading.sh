#!/bin/bash

# Define array of process names
processes=(
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_1.sh"
    "python3 trading_bot.py EUR_USD#1"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_2.sh"
    "python3 trading_bot.py EUR_USD#2"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_3.sh"
    "python3 trading_bot.py EUR_USD#3"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_USD_2.sh"
    "python3 trading_bot.py GBP_USD#2"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CHF_2.sh"
    "python3 trading_bot.py USD_CHF#2"

   )

# Loop through each process name
for process_name in "${processes[@]}"; do
    echo "Stopping $process_name process..."
    pkill -f "$process_name"
done
