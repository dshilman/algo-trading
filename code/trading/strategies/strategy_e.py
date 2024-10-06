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

        if self.long_trading and self.volume > 300 and self.volume == self.volume_max \
                and self.price < self.ema_short  and self.price_momentum_short == self.price_momentum_short_min:
                    if not self.backtest:
                        logger.info(
                            f"Go Long - SELL at ask price: {self.bid}")
                    return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)

        # elif self.short_trading and self.bid > self.bb_high and round(self.rsi, 0) >= 65 \
        #         and self.price_std > self.trading_std and self.price_std_mean > self.trading_std \
        #             and (self.price_std > self.price_std_mean and self.rsi_jump(self.rsi_change) or self.price_std < self.price_std_mean and self.rsi_jump(self.rsi_change - 5)) \
        #                 and self.reverse_rsi_down():
        #                     if not self.backtest:
        #                         logger.info(
        #                             f"Go Short - SELL at bid price: {self.bid}")
        #                     return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)

   


    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_last_trade_time()
        open_trade_price = self.get_open_trade_price()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time or not self.is_trading_time(trading_time):
            close_trade = True

        # if have_units > 0:  # long position            
        #     target_prace = open_trade_price * (1 + self.tp_perc) if open_trade_price is not None else None
        #     if close_trade or (target_prace is not None and self.bid > target_prace or self.bid > self.price_sma_long) and self.reverse_rsi_down(trading_time):
        #         if not self.backtest:
        #             logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}")
        #         return Trade_Action(self.instrument, -have_units, self.ask, False, False)

        elif have_units < 0:  # short position
            target_prace = open_trade_price * (1 - self.tp_perc) if open_trade_price is not None else None
            if close_trade or (target_prace is not None and self.price < target_prace or target_prace is None and self.ask > self.sma_long) \
                or self.price_momentum_long == self.price_momentum_long_max:
                if not self.backtest:
                    logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, False)
  