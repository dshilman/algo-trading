import logging

from strategy import TradingStrategy

logger = logging.getLogger()

class USD_HKD_Strategy (TradingStrategy):

    def __init__(self, instrument, pair_file, api = None, unit_test=False):
        super().__init__(instrument, pair_file, api, unit_test)

