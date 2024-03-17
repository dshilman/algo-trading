import logging
import sys
from pathlib import Path


file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy import TradingStrategy

logger = logging.getLogger()

class TradingStrategy_B(TradingStrategy):

    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)
    
    
    def rsi_spike(self):

        return (self.rsi_max - self.rsi_min >= 5)  and self.rsi < self.high_rsi and self.reverse_rsi_down()

    def rsi_drop(self):

        return (self.rsi_max - self.rsi_min >= 5) and self.rsi > self.low_rsi and self.reverse_rsi_up()

