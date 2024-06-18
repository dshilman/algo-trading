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

        if self.long_trading and self.bid > self.bb_high and self.rsi_max > 80 and self.reverse_rsi_down () \
                and self.rsi_jump() and self.std > self.trading_std:
                if not self.backtest:
                    logger.info(f"Go Short - Sell at ask price: {self.bid}")
                return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)

        elif self.short_trading and self.ask < self.bb_low and self.rsi_min < 20 and self.reverse_rsi_up() \
                and self.rsi_drop() and self.std > self.trading_std:
                    if not self.backtest:
                        logger.info(f"Go Long - Buy at bid price: {self.ask}")
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
            if close_trade or self.bid > target_prace or self.bid > self.bb_high:
                if not self.backtest:
                    logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, False)

        elif have_units < 0:  # short position
            target_prace = open_trade_price * (1 - self.tp_perc) if open_trade_price is not None else None
            if close_trade or self.ask < target_prace or self.ask < self.bb_low:
                if not self.backtest:
                    logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, -have_units, self.ask, False, False)
            
    def reverse_rsi_up(self, trading_time=None):

        return self.rsi - 5 > self.rsi_min
  
    def reverse_rsi_down(self, trading_time=None):

        return self.rsi + 5 < self.rsi_max