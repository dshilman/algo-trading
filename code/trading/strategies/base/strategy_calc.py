import logging
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_base import TradingStrategyBase
from trading.utils.tech_indicators import (calculate_momentum, calculate_rsi)

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
        df = df.tail(self.SMA * 2)
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')
    
        self.data = df

        # logger.debug("After new tickers:\n" + df.iloc[-1:].to_string(header=True))
     
    
    def calc_indicators(self):
        
        df: pd.DataFrame = self.data.copy()

        instrument = self.instrument
        SMA = self.SMA
        DEV = self.DEV

        df["SMA"] = df[instrument].rolling(SMA).mean()
        std = df[instrument].rolling(SMA).std()
        df["Lower"] = df["SMA"] - std * DEV
        df["Upper"] = df["SMA"] + std * DEV

        period = 28

        df["RSI"] = df[instrument].rolling(period).apply(lambda x: calculate_rsi(x.values, period))
        df["RSI_PREV"] = df.RSI.shift()
        
        df["rsi_max"] = df['RSI'].rolling(period).max()
        df["rsi_min"] = df['RSI'].rolling(period).min()


        if not self.backtest and self.print_indicators_count % 60 == 0:
            logger.info("\n" + df.tail().to_string(header=True))
            
        self.print_indicators_count = self.print_indicators_count + 1
    

        self.data = df

    def set_strategy_indicators(self, row: pd.Series=None, time = None):

        if row is None:
            row = self.data.iloc[-1]
            time = self.data.index[-1]
        
        logger.debug(f"Setting strategy indicators for time: {time}")

        self.sma = row ['SMA']
        self.bb_low = round(row ['Lower'], 4)
        self.bb_high =  round(row ['Upper'], 4)

        self.rsi = round(row ['RSI'], 4)
        self.rsi_prev = round(row ['RSI_PREV'], 4)
        self.rsi_max = round(row ['rsi_max'], 4)
        self.rsi_min = round(row ['rsi_min'], 4)
        
        self.ask = row ["ask"]
        self.bid = row ["bid"]

        self.is_trading = True
        if "status" in row:
            self.is_trading = row ["status"] == "tradeable"
        
        if self.rsi == self.rsi_min:
            self.rsi_min_date = time
        elif self.rsi == self.rsi_max:
            self.rsi_max_date = time
  
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

    def risk_time(self, date_time) -> bool:


        logger.debug(f"Date time: {date_time}")

        pause_from_dt = datetime.combine(date_time, datetime.strptime(self.pause_start, '%H:%M:%S').time())
        pause_to_dt = datetime.combine(date_time, datetime.strptime(self.pause_end, '%H:%M:%S').time())


        if pause_from_dt < date_time < pause_to_dt:
            return True

        return False


    def get_last_trade_time(self):

        date_time = None
        
        if len(self.trading_session.trades) > 0:
            date_time_s = self.trading_session.trades[-1][0]
            date_time = datetime.strptime(date_time_s, "%m/%d/%Y %H:%M:%S").replace(tzinfo=None)
        
        return date_time

     
    def reverse_rsi_up(self):

        return round(self.rsi, 0) > round(self.rsi_prev, 0) > round(self.rsi_min, 0)

    def reverse_rsi_down(self):

        return round(self.rsi, 0) < round(self.rsi_prev, 0) < round(self.rsi_max, 0)
        

    def rsi_spike(self):

        return self.rsi_max - self.rsi_min > self.rsi_change \
                and self.rsi_min_date is not None and self.rsi_max_date is not None \
                    and self.rsi_min_date < self.rsi_max_date \

    
    def rsi_drop(self):

        return self.rsi_max - self.rsi_min > self.rsi_change \
                and self.rsi_min_date is not None and self.rsi_max_date is not None \
                    and self.rsi_min_date > self.rsi_max_date \

    
    def reset_rsi(self):
        self.rsi_min_date = None
        self.rsi_max_date = None
