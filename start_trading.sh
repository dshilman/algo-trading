#!/bin/bash

# EUR_USD MACD
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_1.sh' >/dev/null
then
    echo $(date) " EUR_USD#1 Trading bot is already running." 
    echo $(date) " EUR_USD#1 Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_USD#1 Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_USD#1 Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_USD_1.sh &
fi

# EUR_USD Mean Reverse
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_2.sh' >/dev/null
then
    echo $(date) " EUR_USD#2 Trading bot is already running." 
    echo $(date) " EUR_USD#2 Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_USD#2 Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_USD#2 Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_USD_2.sh &
fi

# EUR_USD Mean Reverse
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_3.sh' >/dev/null
then
    echo $(date) " EUR_USD#3 Trading bot is already running." 
    echo $(date) " EUR_USD#3 Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_USD#3 Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_USD#3 Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_USD_3.sh &
fi

# GBP_USD MACD
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_USD_2.sh' >/dev/null
then
    echo $(date) " GBP_USD#2 Trading bot is already running." 
    echo $(date) " GBP_USD#2 Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " GBP_USD#2 Trading bot is not running. Starting it now..." 
    echo $(date) " GBP_USD#2 Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_GBP_USD_2.sh &
fi

# # USD_CHF Momentum
# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CHF_2.sh' >/dev/null
# then
#     echo $(date) " USD_CHF#2 Trading bot is already running." 
#     echo $(date) " USD_CHF#2 Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " USD_CHF#2 Trading bot is not running. Starting it now..." 
#     echo $(date) " USD_CHF#2 Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_USD_CHF_2.sh &
# fi