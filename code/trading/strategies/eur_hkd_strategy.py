import logging

from strategy import TradingStrategy

logger = logging.getLogger()

class EUR_HKD_Strategy (TradingStrategy):

    def __init__(self, instrument, pair_file, api = None, unit_test=False):
        super().__init__(instrument, pair_file, api, unit_test)

    def has_high_rsi(self):
        return self.rsi > self.high_rsi

    def has_low_rsi(self):
        return self.rsi < self.low_rsi