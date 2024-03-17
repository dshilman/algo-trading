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
    

    def calc_indicators(self, resampled_tick_data: pd.DataFrame = None):
        
        df = self.data.copy()
        
        if resampled_tick_data is not None and resampled_tick_data.size > 0:
            df = pd.concat([df, resampled_tick_data])
      
        df = df.tail(self.sma_value * 3)
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

                
        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.sma_value).mean()

        std = df[self.instrument].rolling(self.sma_value).std() * self.dev
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std

        rsi_periods = int(self.sma_value/2)
        period = 14

        df["RSI"] = df[self.instrument][-self.sma_value:].rolling(rsi_periods).apply(lambda x: calculate_rsi(x.values, rsi_periods))

        df ["momentum"] = df[self.instrument][-self.sma_value:].rolling(period).apply(lambda x: calculate_momentum(x.iloc[0], x.iloc[-1]))

        df ["rsi_momentum"] = df.RSI[-self.sma_value:].rolling(period).apply(lambda x: calculate_momentum(x.iloc[0], x.iloc[-1]))
  
        self.ask = round(df.ask.iloc[-1], 6)
        self.bid = round(df.bid.iloc[-1], 6)
        self.sma = round(df.SMA.iloc[-1], 6)
        
        self.bb_lower = round(df.Lower.iloc[-1], 6)
        self.bb_upper =  round(df.Upper.iloc[-1], 6)


        last_rsi = df.RSI[-period:]
        self.rsi = round(last_rsi.iloc[-1], 4)
        self.rsi_min = round(last_rsi.min(), 4)
        self.rsi_max = round(last_rsi.max(), 4)
        self.rsi_mean = round(last_rsi.mean(), 4)


        self.rsi_momentum = round(df ["rsi_momentum"].iloc[-1], 6)
        self.rsi_momentum_prev = round(df ["rsi_momentum"].iloc[-2], 6)

        last_momentum = df.momentum[-period:].values
        self.price_momentum = round(last_momentum[-1], 6)
        self.price_momentum_prev = round(last_momentum[-2], 6)
        last_prices = df[self.instrument][-period:].values
        self.price = round(last_prices[-1], 6)
        self.price_min = round(last_prices[-period:].min(), 6)
        self.price_max = round(last_prices.max(), 6)
        self.price_target = round(self.get_target_price(), 6)

        logger.debug("\n" + df[-period:].to_string(header=True))
  
        self.print_indicators()
        
        self.data = df.copy()

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

    
    def reverse_rsi_up(self):

        return round(self.rsi, self.rsi_round) > round(self.rsi_min, self.rsi_round)

    def reverse_rsi_down(self):
        
        return round(self.rsi, self.rsi_round) < round(self.rsi_max, self.rsi_round)

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

        return (self.rsi_max - self.rsi_min > 5) and (self.rsi_max < self.high_rsi if not self.risk_time(trading_time) else self.high_rsi - 5 ) and self.reverse_rsi_down()

    def rsi_drop(self, trading_time):

        return (self.rsi_max - self.rsi_min > 5) and (self.rsi_min > self.low_rsi if not self.risk_time(trading_time) else self.low_rsi + 5) and self.reverse_rsi_up()
