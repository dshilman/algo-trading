#!/bin/bash

if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_HKD.sh' >/dev/null
then
    echo $(date) " EUR_HKD Trading bot is already running." 
    echo $(date) " EUR_HKD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_HKD Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_HKD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_HKD.sh &
fi

if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_HKD.sh' >/dev/null
then
    echo $(date) " USD_HKD Trading bot is already running." 
    echo $(date) " USD_HKD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " USD_HKD Trading bot is not running. Starting it now..." 
    echo $(date) " USD_HKD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_USD_HKD.sh &
fi

# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD.sh' >/dev/null
# then
#     echo $(date) " EUR_USD Trading bot is already running." 
#     echo $(date) " EUR_USD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " EUR_USD Trading bot is not running. Starting it now..." 
#     echo $(date) " EUR_USD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_EUR_USD.sh &
# fi
