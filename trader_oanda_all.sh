#!/bin/bash

# Check if trading bot scripts are running
SERVICE="trading"
if pgrep -x "$SERVICE" >/dev/null
then
    echo $(date) " Trading bot is not running. Starting it now..." 
    echo $(date) " Trading bot is not running. Starting it now..."  >>/home/ec2-user/algo-trading/logs/trading/time_check.txt
    ./trader_oanda_AUD_SGD.sh & ./trader_oanda_EUR_HKD.sh & ./trader_oanda_EUR_USD.sh & ./trader_oanda_USD_CAD.sh & ./trader_oanda_USD_CHF.sh & ./trader_oanda_USD_HKD.sh &
else
    echo $(date) " Trading bot is already running." 
    echo $(date) " Trading bot is already running." >>/home/ec2-user/algo-trading/logs/trading/time_check.txt
fi