#!/bin/bash

# Check if trading bot scripts are running
if pgrep trader -l > /dev/null
then
    echo $(date) " Trading bot is already running." >>logs/trading/time_check.txt
else
    echo $(date) " Trading bot is not running. Starting it now..."  >>logs/trading/time_check.txt
    ./trader_oanda_AUD_SGD.sh & ./trader_oanda_EUR_HKD.sh & ./trader_oanda_EUR_USD.sh & ./trader_oanda_USD_CAD.sh & ./trader_oanda_USD_CHF.sh & ./trader_oanda_USD_HKD.sh &
fi