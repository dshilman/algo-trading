import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta


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

        if self.short_trading and self.volume > self.trading_volume and self.volume_pct_change > .5 and self.volume == self.volume_max \
            and self.rsi_short_pct_change < -self.rsi_change and self.rsi_short == self.rsi_short_min and self.price - self.price_open < 0 \
                and self.price_momentum_short == self.price_momentum_short_min:
                    if not self.backtest:
                        logger.info(f"Go Short - Sell {self.units_to_trade} units at ask price: {self.bid}")
                    return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)

        elif self.long_trading and self.volume > self.trading_volume and self.volume_pct_change > .5 and self.volume == self.volume_max \
            and self.rsi_short_pct_change > self.rsi_change and self.rsi_short == self.rsi_short_max and  self.price - self.price_open > 0 \
                and self.price_momentum_short == self.price_momentum_short_max:
                    if not self.backtest:
                        logger.info(f"Go Long - Buy {self.units_to_trade} units at ask price: {self.ask}")
                    return Trade_Action(self.instrument, self.units_to_trade, self.ask, True, False)
   


    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_last_trade_time()
        open_trade_price = self.get_open_trade_price()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time or not self.is_trading_time(trading_time):
            close_trade = True

        if have_units > 0:  # long position
            target_prace = open_trade_price * (1 + self.tp_perc) if open_trade_price is not None else None
            if close_trade or (target_prace is not None and self.price > target_prace or target_prace is None and self.ask < self.sma_long):
                    if not self.backtest:
                        logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}")
                    return Trade_Action(self.instrument, -have_units, self.bid, False, False)
 
        elif have_units < 0:  # short position
            target_prace = open_trade_price * (1 - self.tp_perc) if open_trade_price is not None else None
            if close_trade or (target_prace is not None and self.price < target_prace or target_prace is None and self.ask > self.sma_long):
                    if not self.backtest:
                        logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                    return Trade_Action(self.instrument, -have_units, self.ask, False, False)
        