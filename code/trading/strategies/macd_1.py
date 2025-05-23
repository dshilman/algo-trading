import logging
import math
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from numpy import take
import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_macd_base import TradingStrategyMACD
from trading.dom.trade import Trade_Action

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategy(TradingStrategyMACD):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)

    def calc_indicators(self):
        super().calc_indicators()

        df: pd.DataFrame = self.data
 
        df["rsi_short_min"] = df["rsi_short"].rolling(5).min()
        df["rsi_short_max"] = df["rsi_short"].rolling(5).max()
        df['price_volatility'] = ((df['high'] - df['low']) / (df['high'] + df['low']) / 2).rolling(5).mean()    
       
        self.data = df

    def check_if_need_open_trade(self, trading_time) -> Trade_Action: # type: ignore

        if  self.std_dev_long < self.trading_std and self.price_volatility > self.trading_price_volatility:

            if self.macd_crossover_bull and \
                self.rsi_short > self.high_rsi and self.bid < self.bb_high:
                    if not self.backtest:
                        logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                    return Trade_Action(trading_time, self.instrument, self.units_to_trade, self.ask, True, False, False)                    


            elif self.macd_crossover_bear \
                and self.rsi_short < self.low_rsi and self.ask > self.bb_low:
                    if not self.backtest:
                        logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                    return Trade_Action(trading_time, self.instrument, -self.units_to_trade, self.bid, True, False, False)
            
