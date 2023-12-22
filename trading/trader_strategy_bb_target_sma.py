import json
import logging
import logging.handlers as handlers
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytz
import tpqoa

from trader import Trader

logger = logging.getLogger('trader_oanda')
logger.setLevel(logging.INFO)

## Here we define our formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')


class BB_Strategy_SMA_Target_Trader(Trader):
    def __init__(self, conf_file, instrument, bar_length, units_to_trade, SMA, dev, sl_perc = None, tsl_perc = None, tp_perc = None):
        super().__init__(conf_file, instrument, bar_length, units_to_trade, SMA, dev, sl_perc, tsl_perc, tp_perc)
    
       
    def define_strategy(self, resampled_tick_data = None): # "strategy-specific"
        
        super().define_strategy(resampled_tick_data)
        self.target = self.data.SMA.iloc[-1] # not used for stategy bb target bb

        logger.debug ("After defining strategy")
        logger.debug(self.data)

    def determine_action(self, bid, ask):
  
        signal = 0
        price = None
        spread = ask - bid

       
        if self.units > 0: # if already have long positions
            logger.debug (f"Have {self.units} positions, checking if need to close")
            if bid > self.target + spread: # if price is above target SMA, SELL
                signal = -1
                price = bid
                logger.info (f"Signal SELL at price: {round(price, 4)}, sma: {round(self.target, 4)}, spread: {round(spread, 4)}")
        elif self.units < 0: # if alredy have short positions
            if ask < self.target - spread: # price is below target SMA, BUY
                signal = 1
                price = ask
                logger.info (f"Signal BUY at price: {round(price, 4)}, sma: {round(self.target, 4)}, spread: {round(spread, 4)}")

        else: # if no positions
            logger.debug("Don't have any positions, checking if need to open")
            if ask < self.bb_lower: # if price is below lower BB, BUY
                signal = 1
                price = ask
                logger.info (f"Signal BUY at price: {round(price, 4)}, bb_lower: {round(self.bb_lower, 4)}, spread: {round(spread, 4)}")
        
            elif bid > self.bb_upper: # if price is above upper BB, SELL
                signal = -1
                price = bid
                logger.info (f"Signal SELL at price: {round(price, 4)}, bb_upper: {self.bb_upper}, spread: {round(spread, 4)}")

   
        if self.ticks % 100 == 0:
            logger.info (f"Heartbeat current tick {self.ticks} --- instrument: {self.instrument}, ask: {round(ask, 4)}, bid: {round(bid, 4)}, spread: {round(bid - ask, 4)}, signal: {signal}")    


        # if df.distance.iloc[-1] * df.distance.iloc[-2] < 0:
        #     pos = 0

        # df["position"].iloc[-1] = pos
        
        return signal, price

    def on_success(self, time, bid, ask):
        super().on_success(time, bid, ask)
      

    def execute_trades(self, signal, price):

        current_price = price
        
        if self.sl_perc:
            sl_dist = round(current_price * self.sl_perc, 4)            
        else: 
            sl_dist = None
            
            
        if self.tsl_perc:
            tsl_dist = round(current_price * self.tsl_perc, 4) 
        else: 
            tsl_dist = None
            
        
        if self.tp_perc:
            tp_price = round(current_price * (1 + signal * self.tp_perc), 2) 
        else: 
            tp_price = None

        # tp_price = round(self.target, 4)
        
        if signal == 1: # if signal is BUY
            logger.info ("Signal = BUY")
            if self.position < 1:
                order = self.create_order(self.instrument, max(self.units_to_trade, self.units), suppress = True, ret = True,
                                          sl_distance = sl_dist, tsl_distance = tsl_dist, tp_price = tp_price)
                self.report_trade(order, "GOING LONG")            
            else : # Already have a LONG position
                logger.info (f"Already have {self.units} long positions...skipping trade")
            self.position = 1
        elif signal == -1: # if signal is SELL
            logger.info ("Signal = SELL")
            if self.position > -1:
                order = self.create_order(self.instrument, min(-self.units_to_trade, self.units), suppress = True, ret = True,
                                          sl_distance = sl_dist, tsl_distance = tsl_dist, tp_price = tp_price)
                self.report_trade(order, "GOING SHORT")  
            else: # Already have a SHORT position
                logger.info (f"Already have {self.units} short positions...skipping trade")
            self.position = -1
        elif signal == 0: 
            logger.info ("Signal = Neutral - Do nothing")
  

if __name__ == "__main__":
        
    #insert the file path of your config file below!
    days = 1
    stop_after = 10
    args = sys.argv[1:]

    if args and len(args) == 2:
        days = int(args[0])
        stop_after = int(args[1])


    trader = BB_Strategy_SMA_Target_Trader(conf_file = "oanda.cfg",
                       instrument = "EUR_USD", bar_length = 1, units_to_trade = 10000, SMA=100, dev=2, sl_perc = 0.0015, tp_perc = 0.003)
    trader.start_trading(days = days, stop_after = stop_after, max_attempts = 5)
    