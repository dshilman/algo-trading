import logging
import sys
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_exec import TradingStrategyExec

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategy(TradingStrategyExec):
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)

    # def reverse_rsi_up_open(self):

    #     return round(self.rsi, 0) > round(self.rsi_prev, 0) == round(self.rsi_min, 0)
        
    # def reverse_rsi_down_open(self):

    #     return round(self.rsi, 0) < round(self.rsi_prev, 0) == round(self.rsi_max, 0)
        

    # def reverse_rsi_up_close(self):

    #     return self.reverse_rsi_up_open()
        
    # def reverse_rsi_down_close(self):

    #     return self.reverse_rsi_down_open()
   
