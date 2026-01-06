import logging
import sys
from pathlib import Path
import pandas as pd
from trading.strategies.base.strategy_exec import TradingStrategyExec

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.dom.trade import Trade_Action


logger = logging.getLogger()

class TradingStrategyMACD(TradingStrategyExec):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)

    def calc_indicators(self):
        super().calc_indicators()

        df: pd.DataFrame = self.data

        macd_delta: float = 0.0002

        df["near_macd_crossover"] = 0  # Initialize signal column
        df.loc[(df["sma_long"].shift() - df["ema_short"].shift() > 0) & (df["sma_long"].shift() - df["ema_short"].shift() <= macd_delta) & (df["sma_long"] - df["high"] < 0), "near_macd_crossover"] = 1  # Bullish crossover
        df.loc[(df["ema_short"].shift() - df["sma_long"].shift() > 0) & (df["ema_short"].shift() - df["sma_long"].shift() <= macd_delta) & (df["low"] - df["sma_long"] < 0), "near_macd_crossover"] = -1  # Bearish crossover

        # df["near_macd_crossover"] = 0  # Initialize signal column
        # df.loc[((df["sma_long"] - df["ema_short"]) < macd_delta) & ((df["sma_long"] - df["ema_short"]) > 0) & (df["close"] > df["sma_long"]), "near_macd_crossover"] = 1  # Bullish crossover
        # df.loc[((df["ema_short"] - df["sma_long"]) < macd_delta) & ((df["ema_short"] - df["sma_long"]) > 0) & (df["close"] < df["sma_long"]), "near_macd_crossover"] = -1  # Bearish crossover
 
        # df["near_macd_bull"] = (df["near_macd_crossover"] == 1)
        # df["near_macd_bear"] = (df["near_macd_crossover"] == -1)
        # # df["near_macd_bull"] = df["near_macd_crossover"].rolling(2).apply(lambda x: 1 if 1 in x.values else 0)
        # df["near_macd_bear"] = df["near_macd_crossover"].rolling(2).apply(lambda x: 1 if -1 in x.values else 0)
        
        df["macd_crossover"] = 0  # Initialize signal column
        
        df.loc[(df["ema_short"].shift() < df["sma_long"].shift()) & (df["ema_short"] > df["sma_long"]), "macd_crossover"] = 1  # Bullish crossover
        df.loc[(df["ema_short"].shift() > df["sma_long"].shift()) & (df["ema_short"] < df["sma_long"]), "macd_crossover"] = -1  # Bearish crossover
        # df["macd_bull"] = (df["macd_crossover"] == 1)
        # df["macd_bear"] = (df["macd_crossover"] == -1)
        # # df["macd_bull"] = df["macd_crossover"].rolling(2).apply(lambda x: 1 if 1 in x.values else 0)
        # df["macd_bear"] = df["macd_crossover"].rolling(2).apply(lambda x: 1 if -1 in x.values else 0)

        self.data = df

    def set_strategy_indicators(self, row: pd.Series):
        super().set_strategy_indicators(row)

        # self.near_macd_crossover = row["near_macd_crossover"]
        self.near_macd_bull = bool(row["near_macd_crossover"] == 1)
        self.near_macd_bear = bool(row["near_macd_crossover"] == -1)

        # self.macd_crossover = row["macd_crossover"]
        self.macd_bull = bool(row["macd_crossover"] == 1)
        self.macd_bear = bool(row["macd_crossover"] == -1)
