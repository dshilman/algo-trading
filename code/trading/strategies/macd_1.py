import logging
import math
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.utils.tech_indicators import calculate_slope, count_sma_crossover
from trading.strategies.base.strategy_exec import TradingStrategyExec
from trading.dom.trade import Trade_Action

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategy(TradingStrategyExec):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)

    def calc_indicators(self):
        super().calc_indicators()

        df: pd.DataFrame = self.data
 
        # Identify crossovers
        df['macd_crossover'] = 0  # Initialize signal column
        df.loc[(df['ema_short'] > df['sma_long']) & (df['ema_short'].shift(1) < df['sma_long'].shift(1)), 'macd_crossover'] = 1  # Bullish crossover
        df.loc[(df['ema_short'] < df['sma_long']) & (df['ema_short'].shift(1) > df['sma_long'].shift(1)), 'macd_crossover'] = -1  # Bearish crossover
        df['macd_crossover_recent'] = df['macd_crossover'].rolling(5).sum()
        
        df["rsi_short_mean"] = df["rsi_short"].rolling(5).mean()
        df['ema_short_slope'] = df["ema_short"].rolling(15).apply(lambda x: calculate_slope(x))

        df["ema_bb_high_divergance"] = df["bb_upper"] - df["ema_short"]
        df["ema_bb_high_divergance_mean"] = df["ema_bb_high_divergance"].rolling(15).mean()

        df["ema_bb_low_divergance"] = df["ema_short"] - df["bb_lower"]
        df["ema_bb_low_divergance_mean"] = df["ema_bb_low_divergance"].rolling(15).mean()


        self.data = df

    def set_strategy_indicators(self, row: pd.Series):
        super().set_strategy_indicators(row)

        self.macd_crossover = row["macd_crossover"]
        self.macd_crossover_recent = row["macd_crossover_recent"]
 
        self.rsi_short_mean = row["rsi_short_mean"]
        self.ema_short_slope = row["ema_short_slope"]

        self.ema_bb_high_divergance = row["ema_bb_high_divergance"]
        self.ema_bb_low_divergance = row["ema_bb_low_divergance"]

        self.ema_bb_high_divergance_mean = row["ema_bb_high_divergance_mean"]
        self.ema_bb_low_divergance_mean = row["ema_bb_low_divergance_mean"]



    def print_indicators(self):        
        super().print_indicators()
        logger.info(f'sma_long: {round(self.sma_long, 6)}, ema_short: {round(self.ema_short, 6)}, macd_crossover: {round(self.macd_crossover, 0)}, macd_crossover_recent: {round(self.macd_crossover_recent, 0)}')


    def check_if_need_open_trade(self, trading_time) -> Optional[Trade_Action]:
   
        if not self.is_trading_time(trading_time) or self.stop_trading:
            return None
        
        if abs(self.ask - self.bid) > self.trading_spread:
            return None

        if  self.std_dev <= self.trading_std:

            if self.macd_crossover_recent == 1 and self.rsi_short_mean > 80 and self.price < self.bb_high:
                if not self.backtest:
                    logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, self.units_to_trade, self.ask, True, False)                    


            elif self.macd_crossover_recent == -1 and self.rsi_short_mean < 20 and self.price > self.bb_low:
                if not self.backtest:
                    logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)


    def check_if_need_close_trade(self, trading_time) -> Optional[Trade_Action]:

        have_units = self.trading_session.have_units

        open_trade_price = self.get_open_trade_price()
        close_trade = self.need_close_trade(trading_time)

        if have_units > 0:  # long position
            target_price = open_trade_price * (1 + self.tp_perc) if open_trade_price is not None else None
            if close_trade or target_price is not None and (self.price > target_price) or (self.std_dev > self.trading_std and self.price_max > self.bb_high and round(self.ema_short_slope, 5) <= 0):


                if not self.backtest:
                    logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, False)
                
        elif have_units < 0:  # short position
            target_price = open_trade_price * (1 - self.tp_perc) if open_trade_price is not None else None
            if close_trade or target_price is not None and (self.price < target_price) or (self.std_dev > self.trading_std and self.price_min < self.bb_low and round(self.ema_short_slope, 5) >= 0):

                if not self.backtest:
                   logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, -have_units, self.ask, False, False) 

