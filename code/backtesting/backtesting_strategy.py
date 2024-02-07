import configparser
import logging
import sys
from pathlib import Path  # if you haven't already done so

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.dom.trade import Trade_Action
from trading.strategy import TradingStrategy

logger = logging.getLogger()

class Backtesting_Strategy(TradingStrategy):
    def __init__(self, instrument, pair_file, logger = None, unit_test = False):
        super().__init__(instrument = instrument, pair_file = pair_file, api = None, unit_test = unit_test)


