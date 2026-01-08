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

            if (self.near_macd_bull and self.price_change > 0) and self.ema_short_slope > 0 \
                and self.predicted_error < -0.0001 and self.momentum_short == self.momentum_short_max and self.price_high < self.bb_high:
                    if not self.backtest:
                        logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                    return Trade_Action(trading_time, self.instrument, self.units_to_trade, self.ask, True, False, False)                    


            elif (self.near_macd_bear and self.price_change < 0) and self.ema_short_slope < 0 \
                and self.predicted_error > 0.0001 and self.momentum_short == self.momentum_short_min and self.price_low > self.bb_low:
                    if not self.backtest:
                        logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                    return Trade_Action(trading_time, self.instrument, -self.units_to_trade, self.bid, True, False, False)
            


    def check_if_need_close_trade(self, trading_time) -> Trade_Action: # type: ignore

        have_units = self.trading_session.have_units
        close_trade, trade_duration_sec = self.need_close_trade(trading_time)
        trade_duration_min_sec = divmod(trade_duration_sec, 60)
        open_min = trade_duration_min_sec[0]
        open_seconds = trade_duration_min_sec[1]
        take_profit, trade_pnl = self.take_profit()

        if have_units > 0:  # long position
            if (close_trade and trade_pnl < 0) or (take_profit and self.price_change < 0) or (self.macd_bear and self.price_change < 0):
                    if not self.backtest:
                        logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}, trade duration: {open_min} min {open_seconds} sec, trade profit: {trade_pnl}")
                    return Trade_Action(trading_time, self.instrument, -have_units, self.bid, False, False, take_profit)
                    
        elif have_units < 0:  # short position
            if (close_trade and trade_pnl < 0) or (take_profit and self.price_change > 0) or (self.macd_bull and self.price_change > 0):
                    if not self.backtest:
                        logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}, trade duration: {open_min} min {open_seconds} sec, trade profit: {trade_pnl}")
                    return Trade_Action(trading_time, self.instrument, -have_units, self.ask, False, False, take_profit)
