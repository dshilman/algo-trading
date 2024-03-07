#!/bin/bash

# Define array of process names
processes=(
    # "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_HKD.sh"
    # "python3 trading_bot.py EUR_HKD"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD.sh"
    "python3 trading_bot.py EUR_USD"
    # "/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_HKD.sh"
    # "python3 trading_bot.py USD_HKD"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_USD.sh"
    "python3 trading_bot.py GBP_USD"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CHF.sh"
    "python3 trading_bot.py USD_CHF"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CAD.sh"
    "python3 trading_bot.py USD_CAD"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_GBP.sh"
    "python3 trading_bot.py EUR_GBP"
    "/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_CHF.sh"
    "python3 trading_bot.py EUR_CHF"
   )

# Loop through each process name
for process_name in "${processes[@]}"; do
    echo "Stopping $process_name process..."
    pkill -f "$process_name"
done