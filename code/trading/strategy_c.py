import logging
import sys
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategy_b import TradingStrategy_B
from trading.tech_indicators import (calculate_momentum, calculate_rsi,
                                     calculate_slope)

logger = logging.getLogger()

"""
Same as the base strategy but allows averaging down and up

Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategy_C(TradingStrategy_B):

    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)

    def rsi_spike(self):

        return (self.rsi_max - self.rsi_min > 5) and self.rsi_max < self.high_rsi and self.price < self.price_max

    def rsi_drop(self):

        return (self.rsi_max - self.rsi_min > 5) and self.rsi_min > self.low_rsi and self.price > self.price_min
