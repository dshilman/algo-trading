import logging
import sys
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.dom.trade import Trade_Action
from trading.strategies.base.strategy_exec import TradingStrategyExec

import strategy_e

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategy(strategy_e.TradingStrategy):
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)


    def check_if_need_open_trade(self, trading_time):

        if not self.is_trading_time(trading_time) or self.stop_trading:
            return

        if self.long_trading and self.ask < self.bb_low and self.price - self.price_open > 0 \
            and self.price_momentum_long < 0 \
                and self.rsi_short_min < self.rsi_short < 30 and self.volume_pct_change > .3:
                    if not self.backtest:
                        logger.info(f"Go Long - BUY at ask price: {self.ask}")
                    return Trade_Action(self.instrument, self.units_to_trade, self.ask, True, False)

        elif self.short_trading and self.bid > self.bb_high and self.price - self.price_open < 0 \
            and self.price_momentum_long > 0 \
                and 70 < self.rsi_short < self.rsi_short_max and self.volume_pct_change > .3:
                    if not self.backtest:
                        logger.info(f"Go Short - SELL at bid price: {self.bid}")
                    return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)

   
