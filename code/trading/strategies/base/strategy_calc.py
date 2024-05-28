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
from trading.utils.tech_indicators import (count_sma_crossover, calculate_rsi, calculate_slope, calculate_slope_ema)

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
        self.data = df.tail(self.SMA * 3)

        # logger.debug("After new tickers:\n" + df.iloc[-1:].to_string(header=True))
     
    
    def calc_indicators(self):
        
        df: pd.DataFrame = self.data.copy()

        instrument = self.instrument
        SMA = self.SMA
        DEV = self.DEV

        period = 30
        df["sma"] = df[instrument].rolling(SMA).mean()
        df['ema_short'] = calculate_slope_ema(S = df[instrument], span = period)
        df['ema_short_slope'] = df["ema_short"].rolling(period).apply(lambda x: calculate_slope(x))
        df["ema_short_slope_max"] = df['ema_short_slope'].rolling(period).max()
        df["ema_short_slope_min"] = df['ema_short_slope'].rolling(period).min()

        df["std"] = df[instrument].rolling(SMA).std()
        df["std_mean"] = df['std'].rolling(SMA).mean()

        df["lower"] = df["sma"] - df["std"] * DEV
        df["upper"] = df["sma"] + df["std"] * DEV
        
        period = 60
        df["rsi"] = df[instrument].rolling(period).apply(lambda x: calculate_rsi(x, period))
        df["rsi_prev"] = df.rsi.shift()
        
        period = 30
        df["rsi_max"] = df['rsi'].rolling(period).max()
        df["rsi_min"] = df['rsi'].rolling(period).min()
        
        # df["rsi_slope"] = df["rsi"].rolling(period).apply(lambda x: calculate_slope(x))

        # df["price_max"] = df[instrument].rolling(period).max()
        # df["price_min"] = df[instrument].rolling(period).min()
        # df["price_slope"] = df[instrument].rolling(period).apply(lambda x: calculate_slope(x))
        # df["sma_price_max"] = df[instrument].rolling(SMA * 4).max()
        # df["sma_price_min"] = df[instrument].rolling(SMA * 4).min()


        period = 120
        df["less_sma"] = df["sma"] - df[instrument]
        df["less_sma"] = df["less_sma"].apply(lambda x: 1 if x < 0 else -1 if x > 0 else 0)

        df["greater_sma"] = df["sma"] - df[instrument]
        df["greater_sma"] = df["greater_sma"].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)

        df["sma_crossover"] = df["greater_sma"].rolling(period).apply(lambda x: count_sma_crossover(x))

        if (not self.backtest and self.print_indicators_count % 60 == 0) or self.unit_test:
            logger.info("\n" + df.tail(10).to_string(header=True))
            
        self.print_indicators_count = self.print_indicators_count + 1

        self.data = df


    def set_strategy_indicators(self, row: pd.Series=None, time = None):

        trading_time = time
        if row is None:
            row = self.data.iloc[-1]
            trading_time = self.data.index[-1]
        
        logger.debug("Setting strategy indicators")

        self.sma = row ['sma']
        self.ema_short_slope = row ["ema_short_slope"]
        self.ema_short_slope_max = row ["ema_short_slope_max"]
        self.ema_short_slope_min = row ["ema_short_slope_min"]


        self.bb_low = row ['lower']
        self.bb_high =  row ['upper']
        self.std = row ['std']
        self.std_mean = row ['std_mean']

        self.sma_crossover = row ['sma_crossover']

        self.rsi = round(row ['rsi'], 4)
        self.rsi_prev = round(row ['rsi_prev'], 4)
        self.rsi_max = round(row ['rsi_max'], 4)
        self.rsi_min = round(row ['rsi_min'], 4)
        
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
            self.rsi_min_sma = self.sma
        elif self.rsi == self.rsi_max:
            self.rsi_max_price = self.price
            self.rsi_max_time = trading_time
            self.rsi_max_sma = self.sma
  
    def print_indicators(self):

        indicators = [[self.ask, self.bid, self.sma, self.bb_low, self.bb_high, self.rsi, self.rsi_prev, self.rsi_min, self.rsi_max]]
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

        # return self.rsi != self.rsi_min and self.rsi_prev != self.rsi_min and round((self.rsi + self.rsi_prev - .5) / 2, 0) > round(self.rsi_min, 0)
        return self.rsi > self.rsi_prev > self.rsi_min or self.rsi - 1 > self.rsi_prev == self.rsi_min

    def reverse_rsi_down(self, trading_time=None):

        # return self.rsi != self.rsi_max and self.rsi_prev != self.rsi_max and round((self.rsi + self.rsi_prev + .5) / 2, 0) < round(self.rsi_max, 0)
        return self.rsi < self.rsi_prev < self.rsi_max or self.rsi + 1 < self.rsi_prev == self.rsi_max

    
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
