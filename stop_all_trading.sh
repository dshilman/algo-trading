#!/bin/bash

processes=("\"/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_HKD.sh\"",
"\"python3 trading_bot.py EUR_HKD\"",
"\"/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD.sh\"",
"\"python3 trading_bot.py EUR_USD\"",
"\"/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_HKD.sh\"",
"\"python3 trading_bot.py USD_HKD\"",
"\"/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_USD.sh\"",
"\"python3 trading_bot.py GBP_USD\"",
"\"/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CHF.sh\"",
"\"python3 trading_bot.py USD_CHF\"",
"\"/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CAD.sh\"",
"\"python3 trading_bot.py USD_CAD\""
)

# Loop through each process name
for process_name in "${processes[@]}"; do
    # echo "Stopping $process_name process..."
    # ./stop_trader_bot.sh "$process_name"
    pkill -f "$process_name"
done