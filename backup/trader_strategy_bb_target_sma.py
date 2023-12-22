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

logger = logging.getLogger('trader_oanda')
logger.setLevel(logging.DEBUG)

## Here we define our formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')


logHandler = handlers.RotatingFileHandler('strategy_bb_sma.log', maxBytes=5*1024*1024, backupCount=5)
logger.addHandler(logHandler)
logHandler.setFormatter(formatter)


class Trader(tpqoa.tpqoa):
    def __init__(self, conf_file, instrument, bar_length, units_to_trade, SMA, dev, sl_perc = None, tsl_perc = None, tp_perc = None):
        super().__init__(conf_file)
        self.instrument = instrument
        self.bar_length = timedelta(minutes = bar_length)
        self.refresh_strategy_time = timedelta(minutes = 5)
        self.tick_data = pd.DataFrame()
        self.data = None 
        self.last_bar = None
        self.units = 0
        self.units_to_trade = units_to_trade
        self.position = 0
        self.profits = [] 
        self.sl_perc = sl_perc 
        self.tsl_perc = tsl_perc 
        self.tp_perc = tp_perc 

        # *****************add strategy-specific attributes here******************
        self.SMA = SMA
        self.dev = dev
        # ************************************************************************

        self.bb_lower = None
        self.bb_upper =  None
        self.target = None

    
    def get_most_recent(self, days = 1):
        
        self.last_bar = None
        self.data = None

        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = days)
        
        logger.debug (f"Getting candles for {self.instrument}, from {past} to {now}")
        
        df = self.get_history(instrument = self.instrument, start = past, end = now,
                                granularity = "M1", price = "M", localize = True).c.dropna().to_frame()
        df.rename(columns = {"c":self.instrument}, inplace = True)
        # df = df.resample("1M", label = "right").last().dropna().iloc[:-1]

        self.last_bar = df.index[-1].to_pydatetime(warn=False).replace(tzinfo=None)

        logger.debug ("starting df")
        logger.debug(df)

        self.data = df
            
    def start_trading(self, days, stop_after = 10, max_attempts = 5):

        logger.info("\n" + 100* "-")
        success = True

        for i in range(max_attempts):
            try:
                logger.info ("Started New Trading Session")
                logger.info (f"Getting  candles for: {self.instrument}")
                self.get_most_recent(days)

                logger.info ("Define strategy for the first time")
                self.define_strategy()

                logger.info ("Check  Positions")
                self.check_positions()

                logger.info (f"Starting to stream for: {self.instrument}")
                self.stream_data(self.instrument, stop= stop_after)

                success = True

                break
                
            except Exception as e:
                logger.exception(f"Attempt: {i + 1}, Exception occurred")
                success = False

        if success:
            self.terminate_session("Finished Trading Session")
        else:
            self.terminate_session("Finished Trading Session with Errors")


    def on_success(self, time, bid, ask):

        # 2023-12-19T13:28:35.194571445Z
        recent_tick = pd.to_datetime(time).to_pydatetime(warn=False).replace(tzinfo=None).replace(microsecond=0)
        # recent_tick = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=None).replace(microsecond=0)

        logger.debug(f"{self.ticks} ----- time: {recent_tick}  ---- ask: {ask} ----- bid: {bid}")

         # logger.debug(f"{self.ticks}, time: {time}, ask: {ask}, bid: {bid}", flush = True)
        
        df = pd.DataFrame({self.instrument: (ask + bid)/2}, index=[recent_tick])
        self.tick_data = pd.concat([self.tick_data, df])
 
        if recent_tick.replace(tzinfo=None) - self.last_bar >= self.refresh_strategy_time:
            resampled_tick_data = self.resample()
            self.define_strategy(resampled_tick_data)
            self.check_positions()

        signal, price = self.determine_action(bid, ask)

        if signal != 0:
            self.check_positions()
            self.execute_trades(signal, price) 

            
    def resample(self) -> pd.DataFrame:

        df = self.tick_data.copy()
        self.tick_data = pd.DataFrame()

        self.last_bar = df.index[-1].to_pydatetime(warn=False).replace(tzinfo=None)

        logger.debug ("Before resampling")
        logger.debug(df)

        # self.tick_data.resample(self.bar_length, label="right").last().ffill().iloc[:-1]
        df = df.resample("1Min").last()
        df.reset_index(inplace=True)
        df.rename(columns = {"index":'time'}, inplace = True)
        df.set_index('time', inplace=True)    

        logger.debug ("After resampling")
        logger.debug(df)

        return df
        
        
    def define_strategy(self, resampled_tick_data = None): # "strategy-specific"
        
        df = self.data.copy()
        
        if resampled_tick_data is not None and resampled_tick_data.size > 0:
            df = pd.concat([df, resampled_tick_data])
            logger.debug ("Concatenated")
            logger.debug (df)            
      
        df = df.tail(self.SMA * 2)

        logger.debug ("Ready for strategy")
        logger.debug (df)            

        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.SMA).mean()
        std = df[self.instrument].rolling(self.SMA).std() * self.dev

        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std

        # df.dropna(subset=['Lower'], inplace=True)

        df["distance"] = df[self.instrument] - df.SMA
        
        df["signal"] = np.where(df[self.instrument] < df.Lower, 1, np.nan)

        df["signal"] = np.where(df[self.instrument] > df.Upper, -1, np.nan)
        
        # df["position"] = np.where(df.distance * df.distance.shift(1) < 0, 0, df["position"])

        df["signal"] = df.signal.ffill().fillna(0)
        # ***********************************************************************

        self.bb_lower = df.Lower.iloc[-1]
        self.bb_upper =  df.Upper.iloc[-1]
        self.target = df.SMA.iloc[-1]

        logger.info (f"new Bollinger Band  - lower: {self.bb_lower}, upper: {self.bb_upper}")

        self.data = df.copy()
        
        logger.debug ("After defining strategy")
        logger.debug(self.data)

    def determine_action(self, bid, ask):

        # logger.debug ("Inside determine_action")
        
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
            
            # if self.position == -1:
            #     logger.debug ("Have short positions")
            #     order = self.create_order(self.instrument, self.units, suppress = True, ret = True) 
            #     self.report_trade(order, "GOING NEUTRAL")  
            # elif self.position == 1:
            #     logger.debug ("Have longs positions")
            #     order = self.create_order(self.instrument, -self.units, suppress = True, ret = True)
            #     self.report_trade(order, "GOING NEUTRAL")  
            # self.position = 0
    
    def report_trade(self, order, going):  
        logger.debug(f"Inside report_trade: {json.dumps(order, indent = 2)}")
        self.order_id = order.get("id")
        if self.order_id == None:
            logger.info ("Order has been submitted but not filled")
             
        time = order.get("time")
        units = order.get("units")
        price = order.get("price")
        pl = float(order.get("pl"))
        self.profits.append(pl)
        cumpl = sum(self.profits)
        logger.info("\n" + 100* "-")
        logger.info("{} | {}".format(time, going))
        logger.info("{} | units = {} | price = {} | P&L = {} | Cum P&L = {}".format(time, units, price, pl, cumpl))
        logger.info(100 * "-" + "\n")  
        
    def terminate_session(self, cause):
        self.stop_stream = True
        # if self.position != 0:
        #     close_order = self.create_order(self.instrument, units = -self.position * self.units,
        #                                     suppress = True, ret = True) 
        #     self.report_trade(close_order, "GOING NEUTRAL")
        #     self.position = 0
        logger.info (cause)
        logger.info("\n" + 100* "-")

    
    def check_positions(self): 
        logger.debug ("inside check_positions")
        
        self.units = 0
        positions = self.get_positions()
        for position in positions:
            if position["instrument"] == self.instrument:
                self.units = round(float(position["long"]["units"]) + float(position["short"]["units"]), 0)
                logger.info (f"Currently have: {self.units} position of {self.instrument}")
        

        if self.units == 0:
            self.position = 0
        elif self.units > 0:
            self.position = 1
        elif self.units < 0:
            self.position = -1
        

if __name__ == "__main__":
        
    #insert the file path of your config file below!
    days = 1
    stop_after = 10
    args = sys.argv[1:]

    if args and len(args) == 2:
        days = int(args[0])
        stop_after = int(args[1])


    trader = Trader(conf_file = "oanda.cfg",
                       instrument = "EUR_USD", bar_length = 1, units_to_trade = 10000, SMA=100, dev=2, sl_perc = 0.0015, tp_perc = 0.003)
    trader.start_trading(days = days, stop_after = stop_after, max_attempts = 5)
    