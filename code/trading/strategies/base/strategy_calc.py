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
    

    def add_tickers(self, df: pd.DataFrame):

        self.data = pd.concat([self.data, df])
        self.data = self.data.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')
        self.data = self.data.tail(self.sma_value * 3)
     
    
    def calc_indicators(self):
        
        df: pd.DataFrame = self.data.copy()

        instrument = self.instrument
        SMA = self.sma_value
        dev = self.dev

        df["SMA"] = df[instrument].rolling(SMA).mean()

        std = df[instrument].rolling(SMA).std() * dev
        
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std

        period = 14
        rsi_periods = int(SMA/2)
        df["RSI"] = df[instrument].rolling(rsi_periods).apply(lambda x: calculate_rsi(x.values, rsi_periods))
        df["rsi_momentum"] = df.RSI.rolling(period).apply(lambda x: calculate_momentum(x.iloc[0], x.iloc[-1]))
        df["rsi_momentum_prev"] = df ["rsi_momentum"].shift(1)
        df["rsi_max"] = df ['RSI'].rolling(period).max()
        df["rsi_min"] = df ['RSI'].rolling(period).min()
        df["rsi_mean"] = df ['RSI'].rolling(period).mean()
        df["rsi_mean_prev"] = df ['RSI'].shift(period)
        
        df["price_max"] = df [instrument].rolling(period).max()
        df["price_min"] = df [instrument].rolling(period).min()

        df["momentum"] = df[instrument].rolling(period).apply(lambda x: calculate_momentum(x.iloc[0], x.iloc[-1]))        
        df["momentum_prev"] = df["momentum"].shift(1)
        

        df.dropna(subset=["RSI", "SMA"], inplace = True)

        logger.debug("\n" + df[-period:].to_string(header=True))

        self.data = df.copy()

    def set_strategy_indicators(self, row: pd.Series, print=False):

            self.sma = row ['SMA']

            self.bb_lower = row ['Lower']
            self.bb_upper =  row ['Upper']
                   
            self.rsi = round(row ['RSI'], 4)
            self.rsi_max = round(row ['rsi_max'], 4)
            self.rsi_min = round(row ['rsi_min'], 4)
            self.rsi_mean = round(row ['rsi_mean'], 4)
            self.rsi_mean_prev = round(row ['rsi_mean_prev'], 4)
                        
            self.rsi_momentum = round(row ["rsi_momentum"], 6)
            self.rsi_momentum_prev = round(row ["rsi_momentum_prev"], 6)
            
            self.price = row [self.instrument]
            self.price_max = row ['price_max']
            self.price_min = row ['price_min']

            self.ask = row ["ask"]
            self.bid = row ["bid"]

            self.price_momentum = row ['momentum']
            self.price_momentum_prev = row ['momentum_prev']

            self.price_target = round(self.get_target_price(), 6)

            if print:
                self.print_indicators()

    def print_indicators(self):

        indicators = [[self.ask, self.bid, self.sma, self.bb_lower, self.bb_upper, self.rsi, self.rsi_min, self.rsi_max, '{0:f}'.format(self.rsi_momentum), '{0:f}'.format(self.price), '{0:f}'.format(self.price_min), '{0:f}'.format(self.price_max), '{0:f}'.format(self.price_momentum), '{0:f}'.format(self.price_target)]]
        columns=["ASK PRICE", "BID PRICE", "SMA", "BB_LOW", "BB_HIGH", "RSI", "RSI MIN", "RSI MAX", "RSI MOMENTUM", "PRICE", "PRICE MIN", "PRICE MAX", "PRICE MOMENTUM", "TARGET PRICE"]
        logger.info("\n" + tabulate(indicators, headers = columns) + "\n")


    def reverse_rsi_momentum(self):
        # do not change this logic
        if self.rsi_momentum > 0:
            return  self.rsi < self.rsi_max
        elif self.rsi_momentum < 0:
            return self.rsi_min < self.rsi
        elif self.rsi_momentum == 0:
            return True

    
    def reverse_rsi_up_sell(self):

        return round(self.rsi, self.rsi_round) > round(self.rsi_min, self.rsi_round)

    def reverse_rsi_down_sell(self):
        
        return round(self.rsi, self.rsi_round) < round(self.rsi_max, self.rsi_round)

    def reverse_rsi_up_buy(self):

        return round(self.rsi_mean, 0) > round(self.rsi_mean_prev, 0)

    def reverse_rsi_down_buy(self):
        
        return round(self.rsi_mean), 0 < round(self.rsi_mean_prev, 0)


    def get_target_price(self):

        target = None
        have_units = self.trading_session.have_units

        if have_units != 0 and len (self.trading_session.trades) > 0:
            transaction_price =  self.trading_session.trades[-1][3]
            # traded_units = self.trading_session.trades[-1][2]

            # target = round(transaction_price + (1 if have_units > 0 else -1) * transaction_price * self.tp_perc, 4)

            if have_units > 0: # long position
                target = min(self.sma,  transaction_price + self.target * (self.ask - self.bid))
       
            elif have_units < 0: # short position
                target = max(self.sma,  transaction_price - self.target * (self.ask - self.bid))
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

    def too_soon(self, trading_time):

        last_tran_time = self.get_last_trade_time()
        return last_tran_time is None or (last_tran_time + timedelta(minutes=30)) > trading_time


    def get_last_trade_time(self):

        date_time = None
        
        if len(self.trading_session.trades) > 0:
            date_time_s = self.trading_session.trades[-1][0]
            date_time = datetime.strptime(date_time_s, "%m/%d/%Y %H:%M:%S").replace(tzinfo=None)
        
        return date_time

    def rsi_spike(self, trading_time):

        return (self.rsi_max - self.rsi_min > 5) and (self.rsi_max < self.high_rsi)

    def rsi_drop(self, trading_time):

        return (self.rsi_max - self.rsi_min > 5) and (self.rsi_min > self.low_rsi)
