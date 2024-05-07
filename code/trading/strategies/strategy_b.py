import logging
import sys
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_exec import TradingStrategyExec
from trading.dom.trade import Trade_Action

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategy(TradingStrategyExec):
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)

    def reverse_rsi_up_open(self):

        return round(self.rsi, 0) > round(self.rsi_prev, 0) == round(self.rsi_min, 0)
        
    def check_if_need_open_trade(self, trading_time):
        
        if not self.is_trading_time(trading_time) or self.stop_trading:
            return
        
        if self.long_trading and self.ask < self.bb_low and self.rsi_drop() and 33 >= round(self.rsi, 0) \
                    and self.cv > self.cv_value \
                        and self.reverse_rsi_up(trading_time):
                            if not self.backtest:
                                logger.info(
                                    f"Go Long - BUY at ask price: {self.ask}, bb low: {self.bb_low}, rsi: {self.rsi}")
                            return Trade_Action(self.instrument, self.units_to_trade, self.ask, True, False)

        elif self.short_trading and self.bid > self.bb_high and self.rsi_spike() and 67 <= round(self.rsi, 0) \
                    and self.cv > self.cv_value \
                        and self.reverse_rsi_down(trading_time):
                            if not self.backtest:
                                logger.info(
                                    f"Go Short - SELL at bid price: {self.bid}, bb high: {self.bb_high}, rsi: {self.rsi}")
                            return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)