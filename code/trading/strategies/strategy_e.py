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

        # less than sma, greater that bb low, rsi is less than 40, ema slope is negative and == min

        if self.long_trading \
            and self.price_ema_long > self.price_sma_long \
            and self.price_ema_short_slope == self.price_ema_short_slope_max > 0 \
            and self.price_std > self.price_std_mean > self.trading_std:
                    if not self.backtest:
                        logger.info(f"Go Long - Buy at price: {self.ask}")
                    return Trade_Action(self.instrument, self.units_to_trade, self.ask, True, False)

        # less than sma, greater that bb low, rsi is less than 40, ema slope is negative and == min
        elif self.short_trading  \
            and self.price_ema_long < self.price_sma_long \
            and self.price_ema_short_slope == self.price_ema_short_slope_min < 0 \
            and self.price_std > self.price_std_mean > self.trading_std:

                    if not self.backtest:
                        logger.info(f"Go Long - Buy at price: {self.bid}")
                    return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)



    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_last_trade_time()
        open_trade_price = self.get_open_trade_price()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time or not self.is_trading_time(trading_time):
            close_trade = True


        if have_units < 0:  # long position
            target_price = open_trade_price * (1 - self.tp_perc) if open_trade_price is not None else None
            if close_trade or target_price and self.ask < target_price or self.price > self.bb_high:
                    if not self.backtest:
                        logger.info(f"Close Short position - Buy {-have_units} units at ask price: {self.ask}")
                    return Trade_Action(self.instrument, -have_units, self.ask, False, False)

        elif have_units > 0:  # short position
            target_price = open_trade_price * (1 + self.tp_perc) if open_trade_price is not None else None
            if close_trade or target_price and self.bid > target_price or self.price < self.bb_low:
                    if not self.backtest:
                        logger.info(f"Close Long position  - Sell {-have_units} units at bid price: {self.bid}")
                    return Trade_Action(self.instrument, -have_units, self.bid, False, False)


    def reverse_rsi_up(self, trading_time=None):

        return self.rsi - 1 > self.rsi_min
  
    def reverse_rsi_down(self, trading_time=None):

        return  self.rsi + 1 < self.rsi_max
  