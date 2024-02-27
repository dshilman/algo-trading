import logging

from api import OANDA_API
from strategy import TradingStrategy
from trading.api import OANDA_API


logger = logging.getLogger()

class EUR_USD_Strategy (TradingStrategy):

    def __init__(self, instrument, pair_file, api: OANDA_API = None, unit_test=False):
        super().__init__(instrument, pair_file, api, unit_test)

