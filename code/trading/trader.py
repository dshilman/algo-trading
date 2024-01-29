import configparser
import json
import logging
import logging.handlers as handlers
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from random import randint

import numpy as np
import pandas as pd
import tpqoa

from trading import MyTT

logger = logging.getLogger('trader_oanda')


class Trade_Action():
    def __init__(self, instrument, units, price, spread, open_trade = False):
        super().__init__()
        self.instrument = instrument
        self.units = units
        self.price = price
        self.spread = spread
        self.open_trade = open_trade


    def __str__(self):
        return f"Trade_Action: instrument: {self.instrument}, units: {self.units}, price: {self.price}, spread: {self.spread}" 

    def __repr__(self):
        return f"Trade_Action: instrument: {self.instrument}, units: {self.units}, price: {self.price}, spread: {self.spread}"       

class Order ():
    def __init__(self, instrument, price, trade_units, sl_dist, tp_price, comment):
        super().__init__()
        self.instrument = instrument
        self.price = price
        self.units = trade_units
        self.sl = sl_dist
        self.tp = tp_price
        self.comment = comment

    def __str__(self):
        return f"Order: instrument: {self.instrument}, units: {self.units}, price: {self.price}, stopp loss: {self.sl}, take profit: {self.tp}, comment: {self.comment}"

    def __repr__(self):
        return f"Order: instrument: {self.instrument}, units: {self.units}, price: {self.price}, stopp loss: {self.sl}, take profit: {self.tp}, comment: {self.comment}"

class Strategy():
    def __init__(self, instrument, pairs_file):
        super().__init__()

        self.instrument = instrument
        
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.sma_value = int(config.get(instrument, 'SMA'))
        self.dev = float(config.get(instrument, 'dev'))

        self.data = None
        # Caculated attributes
        self.bb_upper =  None
        self.bb_lower =  None
        self.sma = None
        self.rsi = None

    def define_strategy(self, resampled_tick_data: pd.DataFrame = None): # "strategy-specific"
        
        df = self.data.copy()
        
        if resampled_tick_data is not None and resampled_tick_data.size > 0:
            df = pd.concat([df, resampled_tick_data])
      
        df = df.tail(self.sma_value * 2)
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.sma_value).mean()
        std = df[self.instrument].rolling(self.sma_value).std() * self.dev
        
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std
        df["RSI"] = df[self.instrument][-self.sma_value:].rolling(29).apply(lambda x: MyTT.RSI(x.dropna().values, N=28))
        df["slope"] = df[self.instrument][-self.sma_value:].rolling(10).apply(lambda x: MyTT.SLOPE(x.dropna().values, N=10))
        df["slope_prev"] = df["slope"].shift(1)
        self.rsi_max = df ['RSI'][-10:].max()
        self.rsi_min = df ['RSI'][-10:].min()
        self.rsi_mean = df ['RSI'][-10:].mean()
        
        self.price_max = round(df [self.instrument][-10:].max(), 6)
        self.price_min = round(df [self.instrument][-10:].min(), 6)
        self.price_mean = round(df [self.instrument][-10:].mean(), 6)

        logger.debug (df)

        current_price = round(df[self.instrument].iloc[-1], 6)
        self.bb_lower = round(df.Lower.iloc[-1], 6)
        self.bb_upper =  round(df.Upper.iloc[-1], 6)
        self.sma = round(df.SMA.iloc[-1], 6)
        self.rsi = df.RSI.iloc[-1]
        self.slope = df.slope.iloc[-1]
        self.slope_prev = df.slope_prev.iloc[-1]

        self.print_indicators(current_price)
    
        self.data = df.copy()

    def print_indicators(self, price):

        indicators = [[price, self.price_min, self.price_max, self.sma, self.bb_lower, self.bb_upper, self.rsi, self.rsi_min, self.rsi_max, self.rsi_mean, self.slope]]
        df = pd.DataFrame(data=indicators, columns=["PRICE", "PRICE MIN", "PRICE MAX", "SMA", "BB_LOW", "BB_HIGH", "RSI", "RSI MIN", "RSI MAX", "RSI MEAN", "PRICE SLOPE"])
        logger.info("\n" + df.to_string(header=True))


    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units) -> Order:
        
        order = None
        sl_dist = None
        tp_price = None
        comment = None

        # if trade_action.open_trade:
        if sl_perc:
            if trade_action.spread / trade_action.price >= sl_perc:
                logger.warning(f"Current spread: {trade_action.spread} is too large for price: {trade_action.price} and sl_perc: {sl_perc}")
                return None
            """
                Have been getting STOP_LOSS_ON_FILL_DISTANCE_PRECISION_EXCEEDED when trading GBP_JPY
                I assume that the price is too high for 4 digit decimals, thus adding a rule
                if the price is grater that $100, do not use decimals for stop loss
            """
            sl_dist = round(trade_action.price * sl_perc, (4 if trade_action.price < 100 else 0))

            
        if tp_perc:
            tp_price = str(round(trade_action.price + (1 if trade_action.units > 0 else -1) * trade_action.price * tp_perc, (4 if trade_action.price < 100 else 0)))

        if have_units >= 0 and trade_action.units > 0:
            comment = "Going Long"
        elif have_units <= 0 and trade_action.units < 0:
            comment = "Going Short"
        elif have_units > 0 and trade_action.units < 0:
            comment = "Closing Long"
        elif have_units < 0 and trade_action.units > 0:
            comment = "Closing Short"

        order = Order(
            instrument = trade_action.instrument,
            price = trade_action.price,
            trade_units = trade_action.units,
            sl_dist = sl_dist,
            tp_price = tp_price,
            comment = comment
        )
        logger.debug(order)

        return order    

    def determine_action(self, bid, ask, have_units, units_to_trade) -> Trade_Action:
        
        price = round((bid + ask)/2, 6)
        spread = round(ask - bid, 4)
        instrument = self.instrument

        if have_units != 0:  # if already have positions
            logger.debug(f"Have {have_units} positions, checking if need to close")
            trade = self.check_if_need_close_trade(instrument, have_units, price, spread)
            if trade is not None:
                return trade

        # check if need to open a new position
        if spread >= abs(self.bb_upper - self.sma):                            
            logger.warning (f"Current spread: {spread} is too large to trade for possible gain: {round(abs(self.bb_upper - self.sma), 6)}")
            return None
                
        logger.debug(f"Have {have_units} positions, checking if need to open")
        trade = self.check_if_need_open_trade(instrument, have_units, price, spread, units_to_trade)
        if trade is not None:
            return trade

        return None

class Trader(tpqoa.tpqoa):
    def __init__(self, conf_file, pair_file, strategy, unit_test = False):
        super().__init__(conf_file)

        self.refresh_strategy_time = 30 # 30 seconds

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
        self.start = config.get(self.instrument, 'start')
        self.end = config.get(self.instrument, 'end')


        self.tick_data = []
        self.trades = []

        self.units = 0
        
        self.stop_refresh = False
        self.is_trading_time: bool = self.check_trading_time(self.start, self.end)
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
        if not self.is_trading_time:
            logger.info("Not Trading Time")
            return

        for i in range(1, max_attempts + 1):
            try:

                success = True

                if not self.is_trading_time:
                    logger.info("Not Trading Time")
                    continue

                logger.info ("Started New Trading Session")
                logger.info (f"Getting  candles for: {self.instrument}")
                self.strategy.data = self.get_most_recent(self.instrument, self.days)

                logger.info ("Starting Refresh Strategy Thread")
                self.stop_refresh = False
                self.refresh_thread = threading.Thread(target=self.refresh_strategy, args=(self.refresh_strategy_time,))
                self.refresh_thread.start()
                
                time.sleep(1)

                if self.refresh_thread == None or not self.refresh_thread.is_alive():
                    raise Exception("Refresh Strategy Thread is not alive")

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

        trade_action = self.strategy.determine_action(bid, ask, self.units, self.units_to_trade)

        if trade_action is not None:
            # logger.info(f"trade_action: {trade_action}")
            order = self.strategy.create_order(trade_action, self.sl_perc, self.tp_perc, self.units)

            if order is not None:
                self.submit_order(order)
                if self.print_trades:
                    self.trades.append([bid, ask, self.strategy.sma, self.strategy.bb_lower, self.strategy.bb_upper, order.units, order.price, self.units])

        if self.ticks % 100 == 0:
            self.is_trading_time = self.check_trading_time(self.start, self.end)
            if not self.is_trading_time:
                raise Exception("Stop Trading - No longer in trading time")
                
            
        if self.ticks % 250 == 0:
            spread = ask - bid
            spread_prct = spread / ((ask + bid) / 2)
            logger.info(
                f"Heartbeat current tick {self.ticks} --- instrument: {self.instrument}, ask: {round(ask, 4)}, bid: {round(bid, 4)}, spread: {round(spread, 4)}, spread %: {round(spread_prct, 4)}"
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
        if not self.unit_test:        
            oanda_order = self.create_order(instrument = order.instrument, units = order.units, sl_distance = order.sl, tp_price=order.tp, suppress=True, ret=True, comment=order.comment)
            self.report_trade(oanda_order, order.comment)
            if "rejectReason" not in oanda_order:
                self.units = self.units + order.units
                logger.info(f"New # of {order.instrument} units: {self.units}")
            else:
                error = f"Order was not filled: {oanda_order ['type']}, reason: {oanda_order['rejectReason']}"
                logger.error(error)
                raise Exception(error)
        else:
            self.units = self.units + order.units
            logger.info(f"New # of {order.instrument} units: {self.units}")

    def check_trading_time(self, from_date, to_date):

        now = datetime.now()
        today = now.date()

        from_dt = datetime.combine(today, datetime.strptime(from_date, '%H:%M:%S').time())
        to_dt = datetime.combine(today, datetime.strptime(to_date, '%H:%M:%S').time())

        if to_dt < from_dt:
            to_dt = to_dt + timedelta(days=1)

        if not from_dt <= now <= to_dt:
            logger.info(f"Now: {now}, Trading Time: {from_dt} - {to_dt}")
            return False
        else:
            return True


    def refresh_strategy(self, refresh_strategy_time=60):

        i: int = 0
        refresh_check_positions_count = 10

        while not self.stop_refresh:

            logger.debug ("Refreshing Strategy")

            try:

                if refresh_check_positions_count >= 10:
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

                    df = df.resample("30s").last()
                    # df = df.resample("1Min").last()

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

        """
            Close the open position, I have observed that trades open from one day to the next
            have incurred a signifucant loss
        """
        if self.units != 0 and not self.unit_test:
            close_order = self.create_order(self.instrument, units = -self.units, suppress = True, ret = True)
            if not "rejectReason" in close_order:
                self.report_trade(close_order, "Closing Long Position" if self.units > 0 else "Closing Short Position")
                self.units = 0
                trade = [close_order["fullPrice"]["bids"][0]["price"], close_order["fullPrice"]["asks"][0]["price"], self.strategy.sma, self.strategy.bb_lower, self.strategy.bb_upper, float(close_order.get("units")), float(close_order["price"]), self.units]
                self.trades.append(trade)
            else:
                logger.error(f"Close order was not filled: {close_order ['type']}, reason: {close_order['rejectReason']}")

        if self.print_trades and self.trades != None and len(self.trades) > 0:
            df = pd.DataFrame(data=self.trades, columns=["bid", "ask", "sma", "bb_lower", "bb_upper", "trade_units", "price", "have_units"])
            logger.info("\n" + df.to_string(header=True))
            logger.info(f"Oustanding positions: {self.units}")
            df['amount'] = df['price'] * df['trade_units']
            p_and_l = - df['amount'].sum()
            logger.info(f"Session P&L: {round(p_and_l, 4)}")
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

        
