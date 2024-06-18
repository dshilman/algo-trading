import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_base import TradingStrategyBase
from trading.utils.tech_indicators import (count_sma_crossover, calculate_rsi, calculate_slope, calculate_ema)

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategyCalc(TradingStrategyBase):
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)
        
        self.print_indicators_count = 0 

    def add_tickers(self, ticker_df: pd.DataFrame):

        # logger.debug(f"Adding tickers to dataframe: {ticker_df}")

        df = self.data.copy()
        df = pd.concat([df, ticker_df])
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')
        self.data = df.tail(self.SMA * 4)

        # logger.debug("After new tickers:\n" + df.iloc[-1:].to_string(header=True))
     
    
    def calc_indicators(self):
        
        df: pd.DataFrame = self.data.copy()

        instrument = self.instrument

        DEV = self.DEV
        period = self.SMA

        df["std"] = df[instrument].rolling(period).std()
        df["std_mean"] = df['std'].rolling(period).mean()
        df["sma_long"] = df[instrument].rolling(period).mean()
        df["sma_long_prev"] = df["sma_long"].shift()
        df["ema_long"] = df[instrument].rolling(period).apply(lambda x: calculate_ema(S = x))
        # df["ema_long"] = df[instrument].ewm(span=period, adjust=False).mean()
        df["ema_long_prev"] = df["ema_long"].shift()
        df['ema_long_slope'] = df["ema_long"].rolling(period).apply(lambda x: calculate_slope(x))

        df["bb_lower"] = df["sma_long"] - df["std"] * DEV
        df["bb_upper"] = df["sma_long"] + df["std"] * DEV

        period = 30
        df['ema_short'] = df[instrument].rolling(period).apply(lambda x: calculate_ema(S = x))
        df['ema_short_slope'] = df["ema_short"].rolling(period).apply(lambda x: calculate_slope(x))
        df["ema_short_slope_max"] = df['ema_short_slope'].rolling(period).max()
        df["ema_short_slope_min"] = df['ema_short_slope'].rolling(period).min()
       
        period = 30
        df["rsi"] = df[instrument].rolling(period).apply(lambda x: calculate_rsi(x, period))
        df["rsi_prev"] = df.rsi.shift()

        # df['rsi_ema'] = df["rsi"].rolling(period).apply(lambda x: calculate_ema(S = x, span = period))
        # df['rsi_ema_slope'] = df["rsi_ema"].rolling(period).apply(lambda x: calculate_slope(x))
        # df['rsi_ema_slope_prev'] = df["rsi_ema_slope"].shift()
        # df["rsi_ema_slope_max"] = df['rsi_ema_slope'].rolling(period).max()
        # df["rsi_ema_slope_min"] = df['rsi_ema_slope'].rolling(period).min()


        period = 20
        df["rsi_max"] = df['rsi'].rolling(period).max()
        df["rsi_min"] = df['rsi'].rolling(period).min()
        
        # df["price_max"] = df[instrument].rolling(period).max()
        # df["price_min"] = df[instrument].rolling(period).min()
        
        period = 120
 
        df["greater_sma"] = df["sma_long"] - df[instrument]
        df["greater_sma"] = df["greater_sma"].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
        df["sma_crossover"] = df["greater_sma"].rolling(period).apply(lambda x: count_sma_crossover(x))

        df.drop(columns=["greater_sma"], inplace=True)

        if (not self.backtest and self.print_indicators_count % 60 == 0) or self.unit_test:
            logger.info("\n" + df.tail(10).to_string(header=True))
            
        self.print_indicators_count = self.print_indicators_count + 1

        self.data = df


    def set_strategy_indicators(self, row: pd.Series=None, time = None): # type: ignore

        trading_time = time
        if row is None:
            row = self.data.iloc[-1]
            trading_time = self.data.index[-1]
        
        logger.debug("Setting strategy indicators")

        self.sma_long = row ["sma_long"]
        self.sma_long_prev = row ["sma_long_prev"]

        self.ema_long = row ['ema_long']
        self.ema_long_prev = row ['ema_long_prev']

        self.ema_long_slope = row ["ema_long_slope"]
        self.ema_short = row ["ema_short"]
        self.ema_short_slope = row ["ema_short_slope"]
        self.ema_short_slope_max = row ["ema_short_slope_max"]
        self.ema_short_slope_min = row ["ema_short_slope_min"]

        self.bb_low = row ['bb_lower']
        self.bb_high =  row ['bb_upper']
        self.std = row ['std']
        self.std_mean = row ['std_mean']

        self.sma_crossover = row ['sma_crossover']

        self.rsi = round(row ['rsi'], 4)
        self.rsi_prev = round(row ['rsi_prev'], 4)
        self.rsi_max = round(row ['rsi_max'], 4)
        self.rsi_min = round(row ['rsi_min'], 4)
        # self.rsi_ema_slope = row ['rsi_ema_slope']
        # self.rsi_ema_slope_prev = row ['rsi_ema_slope_prev']
        # self.rsi_ema_slope_max = row ["rsi_ema_slope_max"]
        # self.rsi_ema_slope_min = row ["rsi_ema_slope_min"]

        
        self.ask = row ["ask"]
        self.bid = row ["bid"]
        self.price = row [self.instrument]
        # self.price_max = row ["price_max"]
        # self.price_min = row ["price_min"]
        # self.price_slope = round(row ["price_slope"], 4)

        self.is_trading = True
        if "status" in row:
            self.is_trading = row ["status"] == "tradeable"
        
        if self.rsi == self.rsi_min:
            self.rsi_min_price = self.price
            self.rsi_min_time = trading_time
        elif self.rsi == self.rsi_max:
            self.rsi_max_price = self.price
            self.rsi_max_time = trading_time
  
    def print_indicators(self):

        indicators = [[self.ask, self.bid, self.sma_long, self.bb_low, self.bb_high, self.rsi, self.rsi_prev, self.rsi_min, self.rsi_max]]
        columns=["ASK PRICE", "BID PRICE", "SMA", "BB_LOW", "BB_HIGH", "RSI", "RSI PREV", "RSI MIN", "RSI MAX"]
        logger.info("\n" + tabulate(indicators, headers = columns) + "\n")
    
   
    def get_open_trade_price(self):

        have_units = self.trading_session.have_units

        if have_units != 0 and len (self.trading_session.trades) > 0:
            open_trade_price =  self.trading_session.trades[-1][5]

            return open_trade_price

     
        return None

    def is_trading_time(self, date_time) -> bool:

        logger.debug(f"Date time: {date_time}")

        day = date_time.weekday()
        hour = date_time.hour

        if day == 4 and hour >= 20:
            return False


        pause_from_dt = datetime.combine(date_time, datetime.strptime(self.pause_start, '%H:%M:%S').time())
        pause_to_dt = datetime.combine(date_time, datetime.strptime(self.pause_end, '%H:%M:%S').time())


        if pause_from_dt < date_time < pause_to_dt:
            return False
        

        return True


    def get_last_trade_time(self):

        date_time = None
        
        if len(self.trading_session.trades) > 0:
            date_time_s = self.trading_session.trades[-1][0]
            date_time = datetime.strptime(date_time_s, "%m/%d/%Y %H:%M:%S").replace(tzinfo=None)
        
        return date_time

    def get_trade_rsi(self):

        rsi = None
        
        if len(self.trading_session.trades) > 0:
            rsi = self.trading_session.trades[-1][6]
        
        return rsi

     
    def reverse_rsi_up(self, trading_time=None):
        pass
    def reverse_rsi_down(self, trading_time=None):
        pass


    def rsi_jump(self, jump = None):

        if jump is None:
            jump = self.rsi_change

        return self.rsi_max - self.rsi_min > jump \
                and self.rsi_min_time is not None and self.rsi_max_time is not None \
                    and self.rsi_min_time < self.rsi_max_time

    
    def rsi_drop(self, drop = None):

        if drop is None:
            drop = self.rsi_change

        return self.rsi_max - self.rsi_min > drop \
                and self.rsi_min_time is not None and self.rsi_max_time is not None \
                    and self.rsi_min_time > self.rsi_max_time
