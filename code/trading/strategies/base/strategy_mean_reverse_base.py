import logging
import sys
from pathlib import Path
import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.utils.tech_indicators import calculate_slope
from trading.strategies.base.strategy_exec import TradingStrategyExec

logger = logging.getLogger()

class TradingStrategyMeanReverse(TradingStrategyExec):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)


    def calc_indicators(self):
        super().calc_indicators()

        df: pd.DataFrame = self.data

        df["ema_bb_high_divergance"] = df["bb_upper"] - df["ema_short"]
        df["ema_bb_high_divergance_mean"] = df["ema_bb_high_divergance"].rolling(self.period_short).mean()

        df["ema_bb_low_divergance"] = df["ema_short"] - df["bb_lower"]
        df["ema_bb_low_divergance_mean"] = df["ema_bb_low_divergance"].rolling(self.period_short).mean()

        df["ema_short_slope"] = df["ema_short"].rolling(window=self.period_short).apply(calculate_slope)
        df["ema_short_slope_min"] = df["ema_short_slope"].rolling(window=self.period_short).min()
        df["ema_short_slope_max"] = df["ema_short_slope"].rolling(window=self.period_short).max()
        df["ema_short_slope_mean"] = df["ema_short_slope"].rolling(window=self.period_short).mean()


        # df["sma_crossover"] = 0  # Initialize signal column
        # df.loc[(df["open"] < df["sma_long"]) & (df["close"] > df["sma_long"]), "sma_crossover"] = 1  # Bullish crossover
        # df.loc[(df["open"] > df["sma_long"]) & (df["close"] < df["sma_long"]), "sma_crossover"] = -1  # Bearish crossover
        # df["sma_crossover_bull"] = df["sma_crossover"].rolling(int(self.SMA/2)).apply(lambda x: 1 in x.values)
        # df["sma_crossover_bear"] = df["sma_crossover"].rolling(int(self.SMA/2)).apply(lambda x: -1 in x.values)

        
        self.data = df

    def set_strategy_indicators(self, row: pd.Series):
        super().set_strategy_indicators(row)

        self.ema_bb_high_divergance = row["ema_bb_high_divergance"]
        self.ema_bb_low_divergance = row["ema_bb_low_divergance"]

        self.ema_bb_high_divergance_mean = row["ema_bb_high_divergance_mean"]
        self.ema_bb_low_divergance_mean = row["ema_bb_low_divergance_mean"]

        self.ema_short_slope = row["ema_short_slope"]
        self.ema_short_slope_min = row["ema_short_slope_min"]
        self.ema_short_slope_max = row["ema_short_slope_max"]
        self.ema_short_slope_mean = row["ema_short_slope_mean"]


        # self.sma_crossover_bull = bool(row["sma_crossover_bull"])
        # self.sma_crossover_bear = bool(row["sma_crossover_bear"])
