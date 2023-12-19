import json
import time
import traceback
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytz
import tpqoa


class ConTrader(tpqoa.tpqoa):
    def __init__(self, conf_file, instrument, bar_length, units, SMA, dev, sl_perc = None, tsl_perc = None, tp_perc = None):
        super().__init__(conf_file)
        self.instrument = instrument
        self.bar_length = timedelta(minutes = bar_length)
        self.tick_data = pd.DataFrame()
        self.raw_data = None
        self.data = None 
        self.last_bar = None
        self.units = units
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

    
    def get_most_recent(self, days = 1):
        
        self.raw_data = None
        self.last_bar = None

        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = days)
        
        while True:

            if self.last_bar is not None:
                past = self.last_bar

            print (f"Getting candles for {self.instrument}, from {past} to {now}")
            
            df = self.get_history(instrument = self.instrument, start = past, end = now,
                                   granularity = "M1", price = "M", localize = True).c.dropna().to_frame()
            df.rename(columns = {"c":self.instrument}, inplace = True)
            df = df.resample(self.bar_length, label = "right").last().dropna().iloc[:-1]
            
            if self.raw_data is None:
                self.raw_data = df.copy()
            else:
                self.raw_data = pd.concat([self.raw_data, df])

            self.last_bar = self.raw_data.index[-1].to_pydatetime(warn=False).replace(tzinfo=None)

            # print (f"Raw data size: {self.raw_data.size} - Last candle date {self.last_bar}")
            # print (f"bar_length: {self.bar_length}")
            # print (f"now - last_bar: {now - self.last_bar}")

            if now - self.last_bar <= self.bar_length:
                print ("break")
                break
                
        df.rename(columns = {"c":self.instrument}, inplace = True)

        print ("resampled", df)

        self.data = df
            
    def start_trading(self, days, max_attempts = 5, wait = 20, wait_increase = 0):
        
        print (f"Started: {datetime.now()}")

        attempt = 0
        success = False
        while True:
            try:
                print (f"Getting  candles for: {self.instrument}")
                self.get_most_recent(days)

                print ("Define strategy for the first time")
                self.define_strategy()

                print (f"Starting to stream for: {self.instrument}")
                self.stream_data(self.instrument)
            except Exception as e:
                print(e, end = " | ")
                traceback.print_exc() 
            else:
                success = True
                break    
            finally:
                attempt +=1
                print("Attempt: {}".format(attempt), end = '\n')
                if success == False:
                    if attempt >= max_attempts:
                        print("max_attempts reached!")
                        try: # try to terminate session
                            time.sleep(wait)
                            self.terminate_session(cause = "Unexpected Session Stop (too many errors).")
                        except Exception as e:
                            print(e, end = " | ")
                            print("Could not terminate session properly!")
                        finally: 
                            break
                    else: # try again
                        time.sleep(wait)
                        wait += wait_increase
                        self.tick_data = pd.DataFrame()
        
        print (f"Ended: {datetime.now()}")


    def on_success(self, time, bid, ask):

        print(f"# {self.ticks} ---- time: {time} ---- ask: {ask} ----- bid: {bid}")

         # print(f"{self.ticks}, time: {time}, ask: {ask}, bid: {bid}", flush = True)
        
        
        # used for testing only
        if self.ticks >= 100:
            self.terminate_session(cause = "Scheduled Session End.")
            return

        
        recent_tick = pd.to_datetime(time)

        df = pd.DataFrame({self.instrument: (ask + bid)/2}, index=[recent_tick])
        self.tick_data = pd.concat([self.tick_data, df])
 
        if recent_tick.replace(tzinfo=None) - self.last_bar >= self.bar_length:
            self.resample_and_join()
            self.define_strategy()

        pos, price = self.determine_action(bid, ask)

        if pos != 0:
            self.check_positions()
            self.execute_trades(pos, price) 

            
    def resample_and_join(self):

        # self.tick_data.resample(self.bar_length, label="right").last().ffill().iloc[:-1]
        self.tick_data.resample(self.bar_length, label="right").last().ffill()
        self.raw_data = pd.concat([self.raw_data, self.tick_data])
        
        if self.raw_data.size > self.SMA:
            self.raw_data = self.raw_data.tail(self.SMA)

        print ("After resampling", self.raw_data)

        self.tick_data = pd.DataFrame()
        self.last_bar = self.raw_data.index[-1].to_pydatetime(warn=False).replace(tzinfo=None)
        
    def define_strategy(self): # "strategy-specific"
        
        df = self.data.copy()
      
        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.SMA).mean()
        df.dropna(subset=['SMA'], inplace=True)

        df["Lower"] = df["SMA"] - df[self.instrument].rolling(self.SMA).std() * self.dev
        df["Upper"] = df["SMA"] + df[self.instrument].rolling(self.SMA).std() * self.dev
        df["distance"] = df[self.instrument] - df.SMA
        
        df["position"] = np.where(df[self.instrument] < df.Lower, 1, np.nan)

        df["position"] = np.where(df[self.instrument] > df.Upper, -1, np.nan)
        
        df["position"] = np.where(df.distance * df.distance.shift(1) < 0, 0, df["position"])

        df["position"] = df.position.ffill().fillna(0)
        # ***********************************************************************

        self.bb_lower = df["Lower"].iloc[-1]
        self.bb_upper =  df["Upper"].iloc[-1]

        self.data = df.copy()
        
        print ("After defining strategy:", self.data)

    def determine_action(self, bid, ask):

        # print ("Inside determine_action")
        df = self.data.copy()
        pos = 0
        price = None

        # update the latest position

        if ask < self.bb_lower:
           pos = 1
           price = ask
           print (f"Signal BUY at price: {price}, bb_lower: {self.bb_lower}, bb_upper: {self.bb_upper}")
    
        elif bid > self.bb_upper:
           pos = -1
           price = bid
           print (f"Signal SELL at price: {price}, bb_lower: {self.bb_lower}, bb_upper: {self.bb_upper}")

        else:
           pos = 0
           price = ask + (bid - ask)/2
        
        # if df.distance.iloc[-1] * df.distance.iloc[-2] < 0:
        #     pos = 0

        # df["position"].iloc[-1] = pos
        self.data = df.copy()

        return pos, price


    def execute_trades(self, pos, price):

        # print ("Inside execute_trades")
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
            if pos == 1:
                tp_price = round(current_price * (1 + self.tp_perc), 2) 
            elif pos == -1:
                tp_price = round(current_price * (1 - self.tp_perc), 2)      
        else: 
            tp_price = None
        
        if pos == 1:
            print ("Signal = BUY")
            if self.position == 0:
                print ("No current possitions")
                order = self.create_order(self.instrument, self.units, suppress = True, ret = True,
                                          sl_distance = sl_dist, tsl_distance = tsl_dist, tp_price = tp_price)
                self.report_trade(order, "GOING LONG")  
            elif self.position == -1:
                print ("Have short positions")
                order = self.create_order(self.instrument, self.units * 2, suppress = True, ret = True,
                                          sl_distance = sl_dist, tsl_distance = tsl_dist, tp_price = tp_price) 
                self.report_trade(order, "GOING LONG")
            elif self.position == 1:
                print ("Already have long positions...skipping trade")
            self.position = 1
        elif pos == -1: 
            print ("Signal = SELL")
            if self.position == 0:
                print ("No current possitions")
                order = self.create_order(self.instrument, -self.units, suppress = True, ret = True,
                                          sl_distance = sl_dist, tsl_distance = tsl_dist, tp_price = tp_price)
                self.report_trade(order, "GOING SHORT")  
            elif self.position == 1:
                print ("Have longs positions")
                order = self.create_order(self.instrument, -self.units * 2, suppress = True, ret = True,
                                          sl_distance = sl_dist, tsl_distance = tsl_dist, tp_price = tp_price)
                self.report_trade(order, "GOING SHORT")
            elif self.position == -1:
                print ("Already have short positions...skipping trade")
            
            self.position = -1
        elif pos == 0: 
            print ("Signal = Neutral - Do nothing")
            
            # if self.position == -1:
            #     print ("Have short positions")
            #     order = self.create_order(self.instrument, self.units, suppress = True, ret = True) 
            #     self.report_trade(order, "GOING NEUTRAL")  
            # elif self.position == 1:
            #     print ("Have longs positions")
            #     order = self.create_order(self.instrument, -self.units, suppress = True, ret = True)
            #     self.report_trade(order, "GOING NEUTRAL")  
            # self.position = 0
    
    def report_trade(self, order, going):  
        print(f"Inside report_trade: {json.dumps(order, indent = 2)}")
        self.order_id = order.get("id") 
        time = order.get("time")
        units = order.get("units")
        price = order.get("price")
        pl = float(order.get("pl"))
        self.profits.append(pl)
        cumpl = sum(self.profits)
        print("\n" + 100* "-")
        print("{} | {}".format(time, going))
        print("{} | units = {} | price = {} | P&L = {} | Cum P&L = {}".format(time, units, price, pl, cumpl))
        print(100 * "-" + "\n")  
        
    def terminate_session(self, cause):
        self.stop_stream = True
        # if self.position != 0:
        #     close_order = self.create_order(self.instrument, units = -self.position * self.units,
        #                                     suppress = True, ret = True) 
        #     self.report_trade(close_order, "GOING NEUTRAL")
        #     self.position = 0
        # print(cause, end = " | ")
    
    def check_positions(self): 
        print ("inside check_positions")
        
        positions = self.get_positions()
        for position in positions:
            if position["instrument"] == self.instrument:
                self.units = round(float(position["long"]["units"]) + float(position["short"]["units"]), 0)
                print (f"currently have: {self.units}")
        

        if self.units == 0:
            self.position = 0
        elif self.units > 0:
            self.position = 1
        elif self.units < 0:
            self.position = -1
        

if __name__ == "__main__":
        
    #insert the file path of your config file below!
   
    trader = ConTrader(conf_file = "oanda.cfg",
                       instrument = "EUR_USD", bar_length = 1, units = 10000, SMA=125, dev=2, sl_perc = 0.05, tp_perc = 0.01)
    trader.start_trading(days = 1, max_attempts =  1, wait = 20, wait_increase = 0)
    
    
    