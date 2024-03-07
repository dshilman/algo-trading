#!/bin/bash

# EUR_HKD
# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_HKD.sh' >/dev/null
# then
#     echo $(date) " EUR_HKD Trading bot is already running." 
#     echo $(date) " EUR_HKD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " EUR_HKD Trading bot is not running. Starting it now..." 
#     echo $(date) " EUR_HKD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_EUR_HKD.sh &
# fi

# # USD_HKD
# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_HKD.sh' >/dev/null
# then
#     echo $(date) " USD_HKD Trading bot is already running." 
#     echo $(date) " USD_HKD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " USD_HKD Trading bot is not running. Starting it now..." 
#     echo $(date) " USD_HKD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_USD_HKD.sh &
# fi

# EUR_USD
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD.sh' >/dev/null
then
    echo $(date) " EUR_USD Trading bot is already running." 
    echo $(date) " EUR_USD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_USD Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_USD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_USD.sh &
fi

# GBP_USD
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_USD.sh' >/dev/null
then
    echo $(date) " GBP_USD Trading bot is already running." 
    echo $(date) " GBP_USD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " GBP_USD Trading bot is not running. Starting it now..." 
    echo $(date) " GBP_USD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_GBP_USD.sh &
fi

# USD_CAD
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CAD.sh' >/dev/null
then
    echo $(date) " USD_CAD Trading bot is already running." 
    echo $(date) " USD_CAD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " USD_CAD Trading bot is not running. Starting it now..." 
    echo $(date) " USD_CAD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_USD_CAD.sh &
fi

# USD_CHF
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CHF.sh' >/dev/null
then
    echo $(date) " USD_CHF Trading bot is already running." 
    echo $(date) " USD_CHF Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " USD_CHF Trading bot is not running. Starting it now..." 
    echo $(date) " USD_CHF Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_USD_CHF.sh &
fi

# EUR_GBP
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_GBP.sh' >/dev/null
then
    echo $(date) " EUR_GBP Trading bot is already running." 
    echo $(date) " EUR_GBP Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_GBP Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_GBP Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_GBP.sh &
fi


# EUR_CHF
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_CHF.sh' >/dev/null
then
    echo $(date) " EUR_CHF Trading bot is already running." 
    echo $(date) " EUR_CHF Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_CHF Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_CHF Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_CHF.sh &
fi
