#!/bin/bash

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

# AUD_USD
if pgrep -f '/bin/sh /home/ec2-user/algo-trading/trader_oanda_AUD_USD.sh' >/dev/null
then
    echo $(date) " AUD_USD Trading bot is already running." 
    echo $(date) " AUD_USD Trading bot is already running." >>~/algo-trading/logs/trading/time_check.txt
else
    echo $(date) " AUD_USD Trading bot is not running. Starting it now..." 
    echo $(date) " AUD_USD Trading bot is not running. Starting it now..."  >>~/algo-trading/logs/trading/time_check.txt
    ~/algo-trading/trader_oanda_AUD_USD.sh &
fi