import logging
import sys
from pathlib import Path
import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_macd_base import TradingStrategyMACD
from trading.dom.trade import Trade_Action

logger = logging.getLogger()

class TradingStrategy(TradingStrategyMACD):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)


    def check_if_need_open_trade(self, trading_time) -> Trade_Action: # type: ignore

        if self.price_volatility > self.trading_price_volatility:

            if self.near_macd_bull and self.ema_short_slope > 0 \
                and self.predicted_error < -0.0001 and self.momentum_short == self.momentum_short_max and self.price_high < self.bb_high:
                    if not self.backtest:
                        logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                    return Trade_Action(trading_time, self.instrument, self.units_to_trade, self.ask, True, False, False)                    


            elif self.near_macd_bear and self.ema_short_slope < 0 \
                and self.predicted_error > 0.0001 and self.momentum_short == self.momentum_short_min and self.price_low > self.bb_low:
                    if not self.backtest:
                        logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                    return Trade_Action(trading_time, self.instrument, -self.units_to_trade, self.bid, True, False, False)
            
