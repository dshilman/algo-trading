import configparser
import threading
import json
import logging
import logging.handlers as handlers
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytz
import tpqoa

logger = logging.getLogger('trader_oanda')
# logger.setLevel(logging.DEBUG)


class Trade_Action():
    def __init__(self, signal, instrument, price, target, spread):
        super().__init__()
        self.signal = signal
        self.instrument = instrument
        self.price = price
        self.target = target
        self.spread = spread


    def __str__(self):
        return f"Trade_Action: instrument: {self.instrument}, signal: {self.signal}, price: {self.price}, target: {self.target}, spread: {self.spread}" 

    def __repr__(self):
        return f"Trade_Action: instrument: {self.instrument}, signal: {self.signal}, price: {self.price}, target: {self.target}, spread: {self.spread}"       

class Order ():
    def __init__(self, signal, instrument, price, trade_units, sl_dist, tp_price, comment):
        super().__init__()
        self.signal = signal
        self.instrument = instrument
        self.price = price
        self.units = trade_units
        self.sl = sl_dist
        self.tp = tp_price
        self.comment = comment

    def __str__(self):
        return f"Order: instrument: {self.instrument}, units: {self.units}, price: {self.price}, stopp loss: {self.sl}, take profit: {self.tp}"

    def __repr__(self):
        return f"Order: instrument: {self.instrument}, units: {self.units}, price: {self.price}, stopp loss: {self.sl}, take profit: {self.tp}"

class Strategy():
    def __init__(self, instrument, pairs_file):
        super().__init__()

        self.instrument = instrument
        
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.SMA = int(config.get(instrument, 'SMA'))
        self.dev = int(config.get(instrument, 'dev'))

        self.data = None
        # Caculated attributes
        self.bb_upper =  None
        self.target = None


    def define_strategy(self, resampled_tick_data: pd.DataFrame = None): # "strategy-specific"
        
        df = self.data.copy()
        
        if resampled_tick_data is not None and resampled_tick_data.size > 0:
            df = pd.concat([df, resampled_tick_data])
            # logger.debug ("Concatenated")
            # logger.debug (df)            
      
        df = df.tail(self.SMA * 2)

        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.SMA).mean()
        std = df[self.instrument].rolling(self.SMA).std() * self.dev

        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std

        # df.dropna(subset=['Lower'], inplace=True)
        
        df["signal"] = np.where(df[self.instrument] < df.Lower, 1, np.nan)

        df["signal"] = np.where(df[self.instrument] > df.Upper, -1, np.nan)
        
        # df["position"] = np.where(df.distance * df.distance.shift(1) < 0, 0, df["position"])

        df["signal"] = df.signal.ffill().fillna(0)
        # ***********************************************************************

        self.bb_lower = round(df.Lower.iloc[-1], 4)
        self.bb_upper =  round(df.Upper.iloc[-1], 4)
        self.target = round(df.SMA.iloc[-1], 4)

        logger.info (f"new indicators  - bb_lower: {self.bb_lower}, SMA: {self.target}, bb_upper: {self.bb_upper}")

        self.data = df.copy()

    def determine_action(self, bid, ask, units) -> Trade_Action:
        pass

    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units, units_to_trade) -> Order:
        pass

class Trader(tpqoa.tpqoa):
    def __init__(self, conf_file, pair_file, strategy):
        super().__init__(conf_file)

        self.refresh_strategy_time = 5 * 60 # 5 minutes

        self.strategy: Strategy = strategy
        self.instrument = self.strategy.instrument


        config = configparser.ConfigParser()  
        config.read(pair_file)
        self.days = int(config.get(self.instrument, 'days'))
        self.stop_after = int(config.get(self.instrument, 'stop_after'))
        self.print_trades = bool(config.get(self.instrument, 'print_trades'))
        self.units_to_trade = int(config.get(self.instrument, 'units_to_trade'))
        self.sl_perc = float(config.get(self.instrument, 'sl_perc'))
        self.tp_perc = float(config.get(self.instrument, 'tp_perc'))

        self.tick_data = []
        self.trades = []

        self.units = 0
        
        self.stop_refresh = False
        self.unit_test = False

   

        ## Here we define our formatter
        log_file = os.path.join("logs",self.__class__.__name__ + "_" + self.instrument + ".log")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
        logHandler.setFormatter(formatter)

        logger.addHandler(logHandler)

 

    def start_trading(self, max_attempts = 2):

        logger.info("\n" + 100 * "-")

        refresh_thread = None
        for i in range(max_attempts):
            try:
                logger.info ("Started New Trading Session")
                logger.info (f"Getting  candles for: {self.instrument}")
                self.strategy.data = self.get_most_recent(self.instrument, self.days)

                # logger.info ("Define strategy for the first time")
                # self.strategy.define_strategy()

                logger.info ("Starting Refresh Strategy Thread")
                refresh_thread = threading.Thread(target=self.refresh_strategy, args=(self.refresh_strategy_time,))
                refresh_thread.start()
                
                time.sleep(1)

                logger.info (f"Starting to stream for: {self.instrument}")
                self.stream_data(self.instrument, stop= self.stop_after)
          

                self.terminate_session("Finished Trading Session")

                break

            except Exception as e:
                logger.exception(e)
                logger.error(f"Error in attempt {i + 1} of {max_attempts} to start trading")
                self.terminate_session("Finished Trading Session with Errors")
            finally:
                logger.info("Stopping Refresh Strategy Thread")
                self.stop_refresh = True
                if refresh_thread is not None and refresh_thread.is_alive():
                    refresh_thread.join(timeout=self.refresh_strategy_time)
                



    def get_most_recent(self, instrument, days = 1):
        
        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = days)
        
        logger.debug (f"Getting candles for {instrument}, from {past} to {now}")
        
        df = self.get_history(instrument = instrument, start = past, end = now,
                                granularity = "M1", price = "M", localize = True).c.dropna().to_frame()
        df.rename(columns = {"c":instrument}, inplace = True)

        logger.debug ("starting df")
        logger.debug(df)

        return df

  
    def on_success(self, time, bid, ask):

        logger.debug(f"{self.ticks} ----- time: {time}  ---- ask: {ask} ----- bid: {bid}")

        self.capture(time, bid, ask)

        trade_action = self.strategy.determine_action(bid, ask, self.units)

        if trade_action and trade_action.signal != 0:
            # self.check_positions()
            order = self.strategy.create_order(trade_action, self.sl_perc, self.tp_perc, self.units, self.units_to_trade)

            if order != None:
                self.submit_order(order)
                if self.print_trades:
                    self.trades.append([bid, ask, self.strategy.target, self.strategy.bb_lower, self.strategy.bb_upper, trade_action.signal, order.units, order.price, self.units])
            # else:
            #     if self.print_trades:
            #         self.trades.append([bid, ask, self.strategy.target, self.strategy.bb_lower, self.strategy.bb_upper, trade_action.signal, 0, 0, self.units])

        # else:
        #     if self.print_trades:
        #         self.trades.append([bid, ask, self.strategy.target, self.strategy.bb_lower, self.strategy.bb_upper, 0, 0, 0, self.units])

        if self.ticks % 100 == 0:
            spread = ask - bid
            spread_prct = spread / ((ask + bid) / 2)
            logger.info(
                f"Heartbeat current tick {self.ticks} --- instrument: {self.instrument}, ask: {round(ask, 4)}, bid: {round(bid, 4)}, spread: {round(spread, 4)}, spread %: {round(spread_prct, 4)}, signal: {trade_action.signal}"
        )
        

    def capture(self, time, bid, ask):

        # 2023-12-19T13:28:35.194571445Z
        # date_time = pd.to_datetime(time).to_pydatetime(warn=False).replace(tzinfo=None).replace(microsecond=0)
        date_time = pd.to_datetime(time).replace(tzinfo=None)
       
        # date_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=None).replace(microsecond=0)
        
        recent_tick = [date_time, (ask + bid)/2]
        self.tick_data.append(recent_tick)
      

    def submit_order(self, order: Order):

        logger.info(f"Submitting Order: {order}")
        if order != None:
            if not self.unit_test:        
                oanda_order = self.create_order(instrument = order.instrument, units = order.units, sl_distance = order.sl, tp_price = order.tp, suppress=True, ret=True, comment=order.comment)
                self.report_trade(oanda_order, order.comment)
                if oanda_order["rejectReason"] is None:
                    self.units = self.units + order.units
                    logger.info(f"New # of {order.instrument} units: {self.units}")
                else:
                    error = f"Order was not filled: {oanda_order ['type']}, reason: {oanda_order['rejectReason']}"
                    logger.error(error)
                    raise Exception(error)
            else:
                self.units = self.units + order.units
                logger.info(f"New # of {order.instrument} units: {self.units}")

    def refresh_strategy(self, refresh_strategy_time):

        while not self.stop_refresh:

            logger.info ("Refreshing Strategy")

            try:
                self.check_positions()
                
                tick_data = self.tick_data
                self.tick_data = []

                # logger.debug ("Before resampling")
                # logger.debug(tick_data)

                df = None

                if len(tick_data) > 0:
                    df = pd.DataFrame(tick_data, columns=["time", self.instrument])
                    df.reset_index(inplace=True)
                    df.set_index('time', inplace=True)    
                    df.drop(columns=['index'], inplace=True)

                    df = df.resample("1Min").last()

                self.strategy.define_strategy(df)

                time.sleep(refresh_strategy_time)

            except Exception as e:
                logger.exception("Exception occurred while refreshing strategy")
                logger.exception(e)

                self.stop_refresh = True

    
    def report_trade(self, order, comment):

        logger.info("\n" + 100* "-" + "\n")
        logger.info(json.dumps(order, indent = 2))
        # order_id = order.get("id", 0)
        # if order_id == 0:
        #     logger.info ("Order has been submitted but not filled")
            
        # time = order.get("time")
        # units = order.get("units")
        # price = order.get("price")
        # logger.info("\n" + 100* "-")
        # logger.info(f"{comment}")
        # logger.info("order id = {} |  time filled: {}| units = {} | price = {} ".format(order_id,time, units, price))
        logger.info("\n" + 100 * "-" + "\n")

        
    def terminate_session(self, cause):
        # self.stop_stream = True
        logger.info (cause)

        logger.info("\n" + 100* "-")

        if self.print_trades and self.trades != None and len(self.trades) > 0:
            df = pd.DataFrame(data=self.trades, columns=["bid", "ask", "sma", "bb_lower", "bb_upper", "signal", "trade_units", "price", "have_units"])
            logger.info("\n" + df.to_string(header=True))
            logger.info("\n" + 100* "-")
        
        self.trades = []

        # if self.position != 0:
        #     close_order = self.create_order(self.instrument, units = -self.position * self.units,
        #                                     suppress = True, ret = True) 
        #     self.report_trade(close_order, "GOING NEUTRAL")
        #     self.position = 0

    
    def check_positions(self): 

        # logger.debug ("inside check_positions")

        units = 0
        positions = self.get_positions()
        for position in positions:
            instrument = position["instrument"]
            long_units = position["long"]["units"]
            short_units = position["short"]["units"]
            logger.info (f"Currently have position: {instrument} | long_units: {long_units} | short_units: {short_units}")
            if str(instrument).upper() == self.instrument:
                units = round(float(long_units) + float(short_units), 0)
        
        self.units = units
        logger.info (f"Currently have: {units} position of {self.instrument}")

        
