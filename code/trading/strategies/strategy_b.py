import logging
import sys
from pathlib import Path


file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_exec import TradingStrategyExec

logger = logging.getLogger()

class TradingStrategy(TradingStrategyExec):

    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)
    
    
    def rsi_spike(self, trading_time):

        return (self.rsi_max - self.rsi_min > 10) and (self.rsi_mean < self.high_rsi if not self.risk_time(trading_time) else self.rsi_max < self.high_rsi) and self.reverse_rsi_down()

    def rsi_drop(self, trading_time):

        return (self.rsi_max - self.rsi_min > 10) and (self.rsi_mean > self.low_rsi if not self.risk_time(trading_time) else self.rsi_min > self.low_rsi) and self.reverse_rsi_up()

