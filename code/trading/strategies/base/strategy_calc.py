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
from trading.utils.tech_indicators import (calculate_momentum, calculate_rsi,
                                           calculate_slope)

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategyCalc(TradingStrategyBase):
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)
    

    def add_tickers(self, ticker_df: pd.DataFrame):

        # logger.debug(f"Adding tickers to dataframe: {ticker_df}")

        df = self.data.copy()
        df = pd.concat([df, ticker_df])
        # df.dropna(subset=["SMA"], inplace=True)
        df = df.tail(self.sma_config * 2)
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')
    
        self.data = df

        # logger.debug("After new tickers:\n" + df.iloc[-1:].to_string(header=True))
     
    
    def calc_indicators(self):
        
        df: pd.DataFrame = self.data.copy()

        instrument = self.instrument
        SMA = self.sma_config
        dev = self.dev

        df["SMA"] = df[instrument].rolling(SMA).mean()

        std = df[instrument].rolling(SMA).std()
        
        df["Lower"] = df["SMA"] - std * dev
        df["Upper"] = df["SMA"] + std * dev

        rsi_periods = int(SMA/2)
        df["RSI"] = df[instrument].rolling(rsi_periods).apply(lambda x: calculate_rsi(x.values, rsi_periods))
        df["RSI_PREV1"] = df.RSI.shift()
        # df["RSI_PREV2"] = df.RSI.shift(2)


        period = 28
        
        df["rsi_max"] = df ['RSI'].rolling(period).max()
        df["rsi_min"] = df ['RSI'].rolling(period).min()
        
        df["rsi_mom"] = df["RSI"].rolling(period).apply(lambda x: calculate_momentum(x, 1))
        df["rsi_mom_min"] = df["rsi_mom"].rolling(period).min()
        df["rsi_mom_max"] = df["rsi_mom"].rolling(period).max()

        df["price_max"] = df [instrument].rolling(period).max()
        df["price_min"] = df [instrument].rolling(period).min()
    
        logger.debug("\n" + df.iloc[-period:].to_string(header=True))

        self.data = df

    def set_strategy_indicators(self, row: pd.Series=None):

        if row is None:
            row = self.data.iloc[-1]

        self.sma = row ['SMA']
        self.bb_low = round(row ['Lower'], 4)
        self.bb_high =  round(row ['Upper'], 4)
                
        self.rsi = round(row ['RSI'], 4)
        self.rsi_prev1 = round(row ['RSI_PREV1'], 4)
        # self.rsi_prev2 = round(row ['RSI_PREV2'], 4)
        self.rsi_max = round(row ['rsi_max'], 4)
        self.rsi_min = round(row ['rsi_min'], 4)
        
        self.rsi_mom = round(row ['rsi_mom'], 4)
        self.rsi_mom_min = round(row ['rsi_mom_min'], 4)
        self.rsi_mom_max = round(row ['rsi_mom_max'], 4)

        self.price = row [self.instrument]
        self.price_max = row ['price_max']
        self.price_min = row ['price_min']

        self.ask = row ["ask"]
        self.bid = row ["bid"]

        self.price_target = round(self.get_target_price(), 6)

        if not self.backtest:
            self.print_indicators()

    def print_indicators(self):

        indicators = [[self.ask, self.bid, self.sma, self.bb_low, self.bb_high, self.rsi, self.rsi_min, self.rsi_max, self.price_target]]
        columns=["ASK PRICE", "BID PRICE", "SMA", "BB_LOW", "BB_HIGH", "RSI", "RSI MIN", "RSI MAX", "TARGET PRICE"]
        logger.info("\n" + tabulate(indicators, headers = columns) + "\n")
    

    def get_target_price(self):

        target = None
        have_units = self.trading_session.have_units

        if have_units != 0 and len (self.trading_session.trades) > 0:
            transaction_target =  self.trading_session.trades[-1][4]

            return transaction_target

            if have_units > 0: # long position
                target = min(transaction_target, self.sma)       
            elif have_units < 0: # short position
                target = max(transaction_target, self.sma)       
        else:
            target = self.sma

        return target

    def risk_time(self, date_time) -> bool:


        logger.debug(f"Date time: {date_time}")

        pause_from_dt = datetime.combine(date_time, datetime.strptime(self.pause_start, '%H:%M:%S').time())
        pause_to_dt = datetime.combine(date_time, datetime.strptime(self.pause_end, '%H:%M:%S').time())


        if pause_from_dt < date_time < pause_to_dt:
            return True

        return False

    def is_too_soon(self, trading_time):

        last_tran_time = self.get_last_trade_time()
        return last_tran_time is None or (last_tran_time + timedelta(minutes=30)) > trading_time


    def get_last_trade_time(self):

        date_time = None
        
        if len(self.trading_session.trades) > 0:
            date_time_s = self.trading_session.trades[-1][0]
            date_time = datetime.strptime(date_time_s, "%m/%d/%Y %H:%M:%S").replace(tzinfo=None)
        
        return date_time

     
    def reverse_rsi_up(self):

        return self.rsi_mom > self.rsi_mom_min
        # return self.rsi > self.rsi_prev1 >= self.rsi_min
        # self.rsi > self.rsi_prev > self.rsi_min

    def reverse_rsi_down(self):

        return self.rsi_mom < self.rsi_mom_max

        # return self.rsi < self.rsi_prev1 <= self.rsi_max


    def is_rsi_up(self):

        return self.rsi_max - self.rsi_min > self.rsi_change
        #  and self.rsi < 65
        #  and self.price_max - self.price_min < self.bb_upper - self.sma 
        # and self.std > 5 * (self.ask - self.bid)
    
    def is_rsi_down(self):

        return self.rsi_max - self.rsi_min > self.rsi_change
        #  and self.rsi > 35
        #  and self.price_max - self.price_min < self.sma - self.bb_lower 