import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd


file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_exec import TradingStrategyExec
from trading.dom.trade import Trade_Action

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategyMACD(TradingStrategyExec):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)

    def calc_indicators(self):
        super().calc_indicators()

        df: pd.DataFrame = self.data

        df["macd_crossover"] = 0  # Initialize signal column
        df.loc[(df["ema_short"].shift() < df["sma_long"]) & (df["ema_short"] > df["sma_long"]), "macd_crossover"] = 1  # Bullish crossover
        df.loc[(df["ema_short"].shift() > df["sma_long"]) & (df["ema_short"] < df["sma_long"]), "macd_crossover"] = -1  # Bearish crossover
        df["macd_crossover_bull"] = df["macd_crossover"].rolling(5).apply(lambda x: 1 in x.values)
        df["macd_crossover_bear"] = df["macd_crossover"].rolling(5).apply(lambda x: -1 in x.values)
        
        self.data = df

    def set_strategy_indicators(self, row: pd.Series):
        super().set_strategy_indicators(row)

        self.macd_crossover = row["macd_crossover"]
        self.macd_crossover_bull = bool(row["macd_crossover_bull"])
        self.macd_crossover_bear = bool(row["macd_crossover_bear"])

