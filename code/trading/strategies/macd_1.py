import logging
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
        df.loc[(df['ema_short'] > df['sma_long']) & (df['ema_short'].shift(1) <= df['sma_long'].shift(1)), 'macd_crossover'] = 1  # Bullish crossover
        df.loc[(df['ema_short'] < df['sma_long']) & (df['ema_short'].shift(1) >= df['sma_long'].shift(1)), 'macd_crossover'] = -1  # Bearish crossover
        df["macd_crossover_times"] = (df["sma_long"] - df["ema_short"]).apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0).rolling(15).apply(lambda x: count_sma_crossover(x))
 
        df['ema_short_slope'] = df["ema_short"].rolling(15).apply(lambda x: calculate_slope(x))
         
        self.data = df

    def set_strategy_indicators(self, row: pd.Series):
        super().set_strategy_indicators(row)

        self.macd_crossover = row["macd_crossover"]
        self.ema_short_slope = row["ema_short_slope"]
        self.macd_crossover_times = row["macd_crossover_times"]

    def check_if_need_open_trade(self, trading_time) -> Optional[Trade_Action]:
   
        if not self.is_trading_time(trading_time) or self.stop_trading:
            return None
        
        if abs(self.ask - self.bid) > self.trading_spread:
            return None

        if  self.std_dev <= .00055:

            if self.macd_crossover == 1 and self.macd_crossover_times == 1 and self.rsi_short > 65 and self.price < self.bb_high:
                if not self.backtest:
                    logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, self.units_to_trade, self.ask, True, False)                    


            elif self.macd_crossover == -1 and self.macd_crossover_times == 1 and self.rsi_short < 35 and self.price > self.bb_low:
                if not self.backtest:
                    logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)


    def check_if_need_close_trade(self, trading_time) -> Optional[Trade_Action]:

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_open_trade_time()
        open_trade_price = self.get_open_trade_price()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time or not self.is_trading_time(trading_time):
            close_trade = True

        if have_units > 0:  # long position
            target_price = open_trade_price * (1 + self.tp_perc) if open_trade_price is not None else None
            if close_trade or target_price is not None and (self.price_high > target_price) or self.ema_short_slope < 0:
                if not self.backtest:
                    logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, False)
                
        elif have_units < 0:  # short position
            target_price = open_trade_price * (1 - self.tp_perc) if open_trade_price is not None else None
            if close_trade or target_price is not None and (self.price_low < target_price) or self.ema_short_slope > 0:
                if not self.backtest:
                   logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, -have_units, self.ask, False, False) 

