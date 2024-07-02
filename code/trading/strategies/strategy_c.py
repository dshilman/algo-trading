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


    def check_if_need_open_trade(self, trading_time):

        if not self.is_trading_time(trading_time) or self.stop_trading:
            return

        if self.long_trading and self.ask < self.bb_low and round(self.rsi, 0) <= 35 \
                and self.price_std > self.trading_std and self.price_std > self.price_std_mean \
                    and self.rsi_drop(self.rsi_change) and self.sma_crossover > 0 \
                        and self.reverse_rsi_up():
                            if not self.backtest:
                                logger.info(f"Go Long - BUY at ask price: {self.ask}")
                            return Trade_Action(self.instrument, self.units_to_trade, self.ask, True, False)

        elif self.short_trading and self.bid > self.bb_high and round(self.rsi, 0) >= 65 \
                and self.price_std > self.trading_std and self.price_std > self.price_std_mean \
                    and self.rsi_jump(self.rsi_change) and self.sma_crossover > 0 \
                        and self.reverse_rsi_down():
                            if not self.backtest:
                                logger.info(f"Go Short - SELL at bid price: {self.bid}")
                            return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)

   
    # def reverse_rsi_up(self, trading_time=None):

    #     return (self.rsi + self.rsi_prev) / 2 > self.rsi_min and self.rsi_prev != self.rsi_min and self.rsi != self.rsi_min

    # def reverse_rsi_down(self, trading_time=None):

    #     return  (self.rsi + self.rsi_prev) / 2 < self.rsi_max and self.rsi_prev != self.rsi_max and self.rsi != self.rsi_max

    def reverse_rsi_up(self, trading_time=None):

        return self.rsi - 5 > self.rsi_min
  
    def reverse_rsi_down(self, trading_time=None):

        return self.rsi + 5 < self.rsi_max
