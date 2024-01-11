import configparser
import json
import logging
import logging.handlers as handlers
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import tpqoa

import MyTT

logger = logging.getLogger('trader_oanda')


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
        self.dev = float(config.get(instrument, 'dev'))

        self.data = None
        # Caculated attributes
        self.bb_upper =  None
        self.target = None
        self.rsi = None

        self.slope05 = None
        self.slope10 = None
        self.slope05_05 = None
        self.slope10_10 = None

        self.start_s = datetime.now().replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")


    def define_strategy(self, resampled_tick_data: pd.DataFrame = None): # "strategy-specific"
        
        df = self.data.copy()
        
        if resampled_tick_data is not None and resampled_tick_data.size > 0:
            df = pd.concat([df, resampled_tick_data])
            # logger.debug ("Concatenated")
            # logger.debug (df)            
      
        df = df.tail(self.SMA * 2)
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.SMA).mean()
        std = df[self.instrument].rolling(self.SMA).std() * self.dev
        
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std
        df["RSI"] = df [self.instrument].rolling(15).apply(lambda x: MyTT.RSI(x.values, N=14))
        df["slope05"] = df [self.instrument].rolling(5).apply(lambda x: MyTT.SLOPE(x.dropna().values, N=5))
        df["slope10"] = df [self.instrument].rolling(10).apply(lambda x: MyTT.SLOPE(x.dropna().values, N=10))
        df["rsi_slope"] = df ["RSI"].rolling(5).apply(lambda x: MyTT.SLOPE(x.dropna().values, N=5))

        self.bb_lower = round(df.Lower.iloc[-1], 4)
        self.bb_upper =  round(df.Upper.iloc[-1], 4)
        self.target = round(df.SMA.iloc[-1], 4)
        self.rsi = df.RSI.iloc[-1]
        self.rsi_slope = df.rsi_slope.iloc[-1]
        self.rsi_slope_flat = True if self.rsi_slope > -0.25 and self.rsi_slope < 0.25 else False
        self.slope05 = df.slope05.iloc[-1]
        self.slope10 = df.slope10.iloc[-1]

        logger.info (df)

        logger.info ("new indicators:")
        logger.info (f"bb_lower: {self.bb_lower}, SMA: {self.target}, bb_upper: {self.bb_upper}, rsi: {self.rsi}")
        logger.info (f"slope05: {self.slope05}, slope10: {self.slope10}")

        self.data = df.copy()
    

    def determine_action(self, bid, ask, units) -> Trade_Action:
        pass

    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units, units_to_trade) -> Order:
        pass

class Trader(tpqoa.tpqoa):
    def __init__(self, conf_file, pair_file, strategy, unit_test = False):
        super().__init__(conf_file)

        self.refresh_strategy_time = 1 * 60 # 2 minutes

        self.strategy: Strategy = strategy
        self.instrument = self.strategy.instrument
        self.refresh_thread = None


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
        self.unit_test = unit_test

        ## Here we define our formatter
        

        if self.unit_test:
            logger.setLevel(logging.DEBUG)            
        else:
            logger.setLevel(logging.INFO)

        log_file = os.path.join("logs", __name__ + "_" + self.instrument + ".log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

 

    def start_trading(self, max_attempts = 3):

        logger.info("\n" + 100 * "-")

        for i in range(1, max_attempts + 1):
            try:
                success = True

                logger.info ("Started New Trading Session")
                logger.info (f"Getting  candles for: {self.instrument}")
                self.strategy.data = self.get_most_recent(self.instrument, self.days)

                logger.info ("Starting Refresh Strategy Thread")
                self.stop_refresh = False
                self.refresh_thread = threading.Thread(target=self.refresh_strategy, args=(self.refresh_strategy_time,))
                self.refresh_thread.start()
                
                time.sleep(1)

                logger.info (f"Starting to stream for: {self.instrument}")
                self.stream_data(self.instrument, stop= self.stop_after)
                         
                break

            except Exception as e:
                success = False
                logger.exception(e)
                logger.error(f"Error in attempt {i} of {max_attempts} to start trading")
            finally:
                logger.info("Stopping Refresh Strategy Thread")
                self.stop_refresh = True
                if self.refresh_thread is not None and self.refresh_thread.is_alive():
                    self.refresh_thread.join(timeout=self.refresh_strategy_time)
                    logger.info("Stopped Refresh Strategy Thread")

        try:
            self.terminate_session("Finished Trading Session " + "Successfully" if success else "with Errors")
        except Exception as e:
            logger.exception(e)
            logger.error("Error terminating session")



    def get_most_recent(self, instrument, days = 1):
        
        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = days)
        
        logger.debug (f"Getting candles for {instrument}, from {past} to {now}")
        
        df = self.get_history(instrument = instrument, start = past, end = now,
                                granularity = "M1", price = "M", localize = True).c.dropna().to_frame()
        df.rename(columns = {"c":instrument}, inplace = True)

        logger.info (f"history data_frame: {df.shape}")
        return df

  
    def on_success(self, time, bid, ask):

        # logger.debug(f"{self.ticks} ----- time: {time}  ---- ask: {ask} ----- bid: {bid}")

        self.capture(time, bid, ask)

        trade_action = self.strategy.determine_action(bid, ask, self.units)

        if trade_action and trade_action.signal != 0:
            order = self.strategy.create_order(trade_action, self.sl_perc, self.tp_perc, self.units, self.units_to_trade)

            if order != None:
                self.submit_order(order)
                if self.print_trades:
                    self.trades.append([bid, ask, self.strategy.target, self.strategy.bb_lower, self.strategy.bb_upper, trade_action.signal, order.units, order.price, self.units])

        if self.ticks % 500 == 0:
            spread = ask - bid
            spread_prct = spread / ((ask + bid) / 2)
            logger.info(
                f"Heartbeat current tick {self.ticks} --- instrument: {self.instrument}, ask: {round(ask, 4)}, bid: {round(bid, 4)}, spread: {round(spread, 4)}, spread %: {round(spread_prct, 4)}, signal: {trade_action.signal}"
            )
            if self.refresh_thread == None or not self.refresh_thread.is_alive():
                raise Exception("Refresh Strategy Thread is not alive")


    def capture(self, time, bid, ask):

        # 2023-12-19T13:28:35.194571445Z
        date_time = pd.to_datetime(time).replace(tzinfo=None)
        
        recent_tick = [date_time, (ask + bid)/2]
        self.tick_data.append(recent_tick)
      

    def submit_order(self, order: Order):

        logger.info(f"Submitting Order: {order}")
        if order != None:
            if not self.unit_test:        
                oanda_order = self.create_order(instrument = order.instrument, units = order.units, sl_distance = order.sl, suppress=True, ret=True, comment=order.comment)
                self.report_trade(oanda_order, order.comment)
                if not "rejectReason" in oanda_order:
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

        i: int = 0
        refresh_check_positions_count = 6

        while not self.stop_refresh:

            logger.debug ("Refreshing Strategy")

            try:

                if refresh_check_positions_count >= 5:
                    self.check_positions()
                    refresh_check_positions_count = 0

                refresh_check_positions_count += 1

                tick_data = self.tick_data
                self.tick_data = []

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
                i += 1
                if i > 3:
                    self.stop_refresh = True

    
    def report_trade(self, order, comment):

        logger.info("\n" + 100* "-" + "\n")
        logger.info(json.dumps(order, indent = 2))
        logger.info("\n" + 100 * "-" + "\n")

        
    def terminate_session(self, cause):
        # self.stop_stream = True
        logger.info (cause)

        logger.info("\n" + 100* "-")

        # if self.units != 0 and not self.unit_test:
        #     close_order = self.create_order(self.instrument, units = -self.units, suppress = True, ret = True)
        #     if not "rejectReason" in close_order:
        #         self.report_trade(close_order, "GOING NEUTRAL")
        #         self.units = 0
        #         self.trades.append([close_order["fullPrice"]["bids"]["price"], close_order["fullPrice"]["asks"]["price"], self.strategy.target, self.strategy.bb_lower, self.strategy.bb_upper, 1 if close_order.get("units") > 0 else -1, close_order.get("units"), close_order["price"], self.units])
        #     else:
        #         logger.error(f"Close order was not filled: {close_order ['type']}, reason: {close_order['rejectReason']}")

        if self.print_trades and self.trades != None and len(self.trades) > 0:
            df = pd.DataFrame(data=self.trades, columns=["bid", "ask", "sma", "bb_lower", "bb_upper", "signal", "trade_units", "price", "have_units"])
            logger.info("\n" + df.to_string(header=True))
            logger.info("\n" + 100* "-")
        
        self.trades = []

    
    def check_positions(self): 

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

        
