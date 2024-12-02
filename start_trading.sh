#!/bin/bash

# EUR_USD Reverse Mean
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_1.sh' >/dev/null
then
    echo $(date) " EUR_USD#1 Trading bot is already running." 
    echo $(date) " EUR_USD#1 Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_USD#1 Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_USD#1 Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_USD_1.sh &
fi

# EUR_USD Momentum
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_USD_2.sh' >/dev/null
then
    echo $(date) " EUR_USD#2 Trading bot is already running." 
    echo $(date) " EUR_USD#2 Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " EUR_USD#2 Trading bot is not running. Starting it now..." 
    echo $(date) " EUR_USD#2 Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_EUR_USD_2.sh &
fi

# EUR_GBP
# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_GBP.sh' >/dev/null
# then
#     echo $(date) " EUR_GBP Trading bot is already running." 
#     echo $(date) " EUR_GBP Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " EUR_GBP Trading bot is not running. Starting it now..." 
#     echo $(date) " EUR_GBP Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_EUR_GBP.sh &
# fi


## GBP_USD
# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_USD.sh' >/dev/null
# then
#     echo $(date) " GBP_USD Trading bot is already running." 
#     echo $(date) " GBP_USD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " GBP_USD Trading bot is not running. Starting it now..." 
#     echo $(date) " GBP_USD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_GBP_USD.sh &
# fi

## GBP_CHF
# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_GBP_CHF.sh' >/dev/null
# then
#     echo $(date) " GBP_CHF Trading bot is already running." 
#     echo $(date) " GBP_CHF Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " GBP_CHF Trading bot is not running. Starting it now..." 
#     echo $(date) " GBP_CHF Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_GBP_CHF.sh &
# fi



# # USD_CHF
# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_USD_CHF.sh' >/dev/null
# then
#     echo $(date) " USD_CHF Trading bot is already running." 
#     echo $(date) " USD_CHF Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " USD_CHF Trading bot is not running. Starting it now..." 
#     echo $(date) " USD_CHF Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_USD_CHF.sh &
# fi

# EUR_GBP
# if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_EUR_GBP.sh' >/dev/null
# then
#     echo $(date) " EUR_GBP Trading bot is already running." 
#     echo $(date) " EUR_GBP Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
# else
#     echo $(date) " EUR_GBP Trading bot is not running. Starting it now..." 
#     echo $(date) " EUR_GBP Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
#     ~/algo-trading/trader_oanda_EUR_GBP.sh &
# fi

