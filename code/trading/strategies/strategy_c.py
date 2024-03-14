import logging
import sys
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.strategy_b import TradingStrategy_B

logger = logging.getLogger()

class TradingStrategy_C(TradingStrategy_B):

    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)

    def rsi_spike(self):

        return (self.rsi_max - self.rsi_min > 5) and self.rsi_max < self.high_rsi and self.rsi < self.rsi_max

    def rsi_drop(self):

        return (self.rsi_max - self.rsi_min > 5) and self.rsi_min > self.low_rsi and self.rsi > self.rsi_min
