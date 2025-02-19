from math import log
from trading.strategies.base.strategy_calc import TradingStrategyCalc
from trading.dom.trade import Trade_Action
import logging
import sys
from datetime import timedelta
from typing import Optional

from pathlib import Path

import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))


logger = logging.getLogger()


class TradingStrategyExec(TradingStrategyCalc):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test=False):

        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api=api, unit_test=unit_test)

        self.stop_trading = False

    def execute_strategy(self, trading_time):
       
        trade_action = self.determine_trade_action(trading_time)

        if trade_action is not None:
            logger.info(f"{trade_action}")
            order = self.create_order(trade_action, self.sl_perc, self.tp_perc)
            self.submit_order(order)
        else:
            logger.debug("No trade action")

        # if trade_action is not None and trade_action.sl_trade:
        #     raise PauseTradingException(2)

        return

    def determine_trade_action(self, trading_time) -> Trade_Action:


        have_units = self.trading_session.have_units

        if have_units == 0:

            logger.debug(f"Have {have_units} positions, checking if need to open a new trade")
            trade = self.check_if_need_open_trade(trading_time)

        elif abs(have_units) == self.units_to_trade:

            logger.debug(f"Have {have_units} positions, checking for stop loss")
            trade = self.check_for_sl(trading_time, have_units)

            if trade is None:
                logger.debug(f"Have {have_units} positions, checking if need to close a trade")
                trade = self.check_if_need_close_trade(trading_time)
        else:
            trade = None
            
        if trade is not None:            
            self.trading_session.add_trade(trade_action=trade, date_time=trading_time)
        
        return trade
            

    def check_if_need_open_trade(self, trading_time) -> Trade_Action:
        # Implement the logic to determine if a new trade needs to be opened
        # For now, return a default Trade_Action or raise an exception
        raise NotImplementedError("This method needs to be implemented")

    def check_if_need_close_trade(self, trading_time) -> Trade_Action:
        # Implement the logic to determine if a new trade needs to be opened
        # For now, return a default Trade_Action or raise an exception
        raise NotImplementedError("This method needs to be implemented")
    
    

    def check_for_sl(self, trading_time, have_units) -> Trade_Action:

        base_price = None
        
        open_trade_price = self.get_open_trade_price()
        
        if open_trade_price is None:
            return None
        
        if have_units < 0:
            if self.trailing_sl:
                base_price = min(self.price_min, open_trade_price)
            else: 
                base_price = open_trade_price
             
            current_loss_perc = (self.ask - base_price)/base_price
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    logger.info(
                        f"Close short position, - Stop Loss Buy, short price {base_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.ask, False, True)

        elif have_units > 0:
            if self.trailing_sl:
                base_price = max(self.price_max, open_trade_price)
            else: 
                base_price = open_trade_price

            current_loss_perc = (base_price - self.bid)/base_price
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    logger.info(
                        f"Close long position, - Stop Loss Sell, long price {base_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, True)
        
        return None
    
    def need_close_trade(self, trading_time) -> bool:

        if not self.is_trading_time(trading_time):
            return True

        open_trade_time = self.get_open_trade_time()
        close_trade = open_trade_time is not None and (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time

        return close_trade
    