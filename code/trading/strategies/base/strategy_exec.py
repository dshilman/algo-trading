from trading.strategies.base.strategy_calc import TradingStrategyCalc
from trading.dom.trade import Trade_Action
import logging
import sys
from datetime import timedelta

from pathlib import Path

import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))


logger = logging.getLogger()


class TradingStrategyExec(TradingStrategyCalc):
    def __init__(self, trading_strategy, pair_file, api=None, unit_test=False):
        super().__init__(trading_strategy=trading_strategy,
                         pair_file=pair_file, api=api, unit_test=unit_test)

        self.stop_trading = False

    def execute_strategy(self, trading_time):
       
        trade_action = self.determine_trade_action(trading_time)

        if trade_action is not None:
            # logger.info(f"trade_action: {trade_action}")

            order = self.create_order(trade_action, self.sl_perc, self.tp_perc)

            if order is not None:
                self.submit_order(order)
                self.trading_session.open_trade = trade_action.open_trade

        # if trade_action is not None and trade_action.sl_trade:
        #     raise PauseTradingException(2)

        return

    def determine_trade_action(self, trading_time) -> Trade_Action:

        trade: Trade_Action = None
        have_units = self.trading_session.have_units

        if have_units != 0:

            logger.debug(f"Have {have_units} positions, checking for stop loss")
            if self.trading_session.open_trade:
                trade = self.check_for_sl(trading_time, have_units)

                if trade is None:
                    logger.debug(f"Have {have_units} positions, checking if need to close a trade")
                    trade = self.check_if_need_close_trade(trading_time)

        if trade is None and have_units == 0:

            logger.debug(f"Have {have_units} positions, checking if need to open a new trade")
            trade = self.check_if_need_open_trade(trading_time)
            
        if trade is not None:
            self.trading_session.add_trade(trade_action=trade, date_time=trading_time)
        
        return trade
            

    def check_if_need_open_trade(self, trading_time):
        pass


    def reverse_down(self):
        return self.rsi_short_pct_change < 0 and (self.ema_short_slope < 0 or self.price < self.ema_short)

    def reverse_up(self):
        return self.rsi_short_pct_change > 0 and (self.ema_short_slope > 0 or self.price > self.ema_short) 


    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_open_trade_time()
        open_trade_price = self.get_open_trade_price()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time or not self.is_trading_time(trading_time):
            close_trade = True

        if have_units > 0:  # long position
            target_price = open_trade_price * (1 + self.tp_perc) if open_trade_price is not None else None
            if self.reverse_down() and (close_trade or target_price is not None and self.price > target_price):
                    if not self.backtest:
                        logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}")
                    return Trade_Action(self.instrument, -have_units, self.bid, False, False)
 
        elif have_units < 0:  # short position
            target_price = open_trade_price * (1 - self.tp_perc) if open_trade_price is not None else None
            if self.reverse_up() and (close_trade or target_price is not None and self.price < target_price):
                    if not self.backtest:
                        logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                    return Trade_Action(self.instrument, -have_units, self.ask, False, False)


    def check_for_sl(self, trading_time, have_units):


        if len(self.trading_session.trades) == 0:
            return None

        base_price = None
        
        if have_units < 0:
            if self.trailing_sl:
                base_price = min(self.price_min, self.get_open_trade_price())
            else: 
                base_price = self.get_open_trade_price()

            current_loss_perc = (self.ask - base_price)/base_price
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    logger.info(
                        f"Close short position, - Stop Loss Buy, short price {base_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.ask, False, True)

        elif have_units > 0:
            if self.trailing_sl:
                base_price = max(self.price_max, self.get_open_trade_price())
            else: 
                base_price = self.get_open_trade_price()

            current_loss_perc = (base_price - self.bid)/base_price
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    logger.info(
                        f"Close long position, - Stop Loss Sell, long price {base_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, True)
        