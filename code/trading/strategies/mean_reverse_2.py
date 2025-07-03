import logging
import sys
from pathlib import Path

from numpy import average

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.strategies.base.strategy_mean_reverse_base import TradingStrategyMeanReverse
from trading.dom.trade import Trade_Action

logger = logging.getLogger()

class TradingStrategy(TradingStrategyMeanReverse):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api = api, unit_test = unit_test)

    def check_if_need_open_trade(self, trading_time) -> Trade_Action: # type: ignore
   
   
        if  self.std_dev_long > self.trading_std and self.price_volatility > self.trading_price_volatility and abs(self.predicted_error) > .0005:

            if self.rsi_short_max > self.high_rsi \
                and self.price_max > self.bb_high and self.bid > self.ema_short \
                    and self.ema_bb_high_divergance > self.ema_bb_high_divergance_mean > 0:
                        if not self.backtest:
                            logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                        return Trade_Action(trading_time, self.instrument, -self.units_to_trade, self.bid, True, False, False)
                        

            elif self.rsi_short_min < self.low_rsi \
                and self.price_min < self.bb_low and self.ask < self.ema_short \
                    and self.ema_bb_low_divergance > self.ema_bb_low_divergance_mean > 0:
                        if not self.backtest:
                            logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                        return Trade_Action(trading_time, self.instrument, self.units_to_trade, self.ask, True, False, False)                    
