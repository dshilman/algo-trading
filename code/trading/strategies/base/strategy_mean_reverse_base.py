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


        df["bb_high_crossover"] = 0  # Initialize signal column
        df.loc[(df["open"] > df["bb_upper"]) & (df["close"] < df["bb_upper"]), "bb_high_crossover"] = 1  # Bear crossover
        df["bb_high_crossover"] = df["bb_high_crossover"].rolling(5).apply(lambda x: 1 in x.values)

        df["bb_low_crossover"] = 0  # Initialize signal column
        df.loc[(df["open"] < df["bb_lower"]) & (df["close"] > df["bb_lower"]), "bb_low_crossover"] = 1  # Bull crossover
        df["bb_low_crossover"] = df["bb_low_crossover"].rolling(5).apply(lambda x: -1 in x.values)
   
        self.data = df

    def set_strategy_indicators(self, row: pd.Series):
        super().set_strategy_indicators(row)

        self.ema_bb_high_divergance = row["ema_bb_high_divergance"]
        self.ema_bb_low_divergance = row["ema_bb_low_divergance"]

        self.ema_bb_high_divergance_mean = row["ema_bb_high_divergance_mean"]
        self.ema_bb_low_divergance_mean = row["ema_bb_low_divergance_mean"]

        self.bb_high_crossover = row["bb_high_crossover"]
        self.bb_low_crossover = row["bb_low_crossover"]
