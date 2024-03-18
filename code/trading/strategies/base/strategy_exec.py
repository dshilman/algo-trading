import configparser
import json
import logging
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from random import randint

import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.api.oanda_api import OandaApi
from trading.dom.order import Order
from trading.dom.trade import Trade_Action
from trading.dom.trading_session import Trading_Session
from trading.strategies.base.strategy_calc import TradingStrategyCalc
from trading.utils.errors import PauseTradingException
from trading.utils.tech_indicators import (calculate_momentum, calculate_rsi,
                                           calculate_slope)

logger = logging.getLogger()

class TradingStrategyExec(TradingStrategyCalc):
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)
    

    def execute_strategy(self):

        trading_time = datetime.utcnow()
        trade_action = self.determine_trade_action(trading_time)        

        if trade_action is not None:
            # logger.info(f"trade_action: {trade_action}")
            
            order = self.create_order(trade_action, self.sl_perc, self.tp_perc)

            if order is not None:
                self.submit_order(order)
                self.trading_session.add_trade(trade_action=trade_action, rsi=self.rsi)


        if trade_action is not None and trade_action.sl_trade:
            raise PauseTradingException(2)

        return
    

    def determine_trade_action(self, trading_time) -> Trade_Action:

        have_units = self.trading_session.have_units

        if have_units != 0:  # if already have positions             
            logger.debug(f"Have {have_units} positions, checking if need to close")
            trade = self.check_if_need_close_trade(trading_time)
            if trade is not None:
                return trade

        if have_units == 0 or (abs(have_units / self.units_to_trade) < 2 and not self.too_soon(trading_time)):
            logger.debug(f"Have {have_units} positions, checking if need to open")
            trade = self.check_if_need_open_trade(trading_time)
            if trade is not None:
                return trade

        if have_units != 0:  # if already have positions             
            logger.debug(f"Have {have_units} positions, checking for stop loss")
            trade_action = self.check_for_sl(trading_time)
            if trade_action is not None:
                return trade_action
      

        return None
        

    def check_if_need_open_trade(self, trading_time):

        have_units = self.trading_session.have_units
        
        spread = round(self.ask - self.bid, 4)

        if self.ask < self.bb_lower and self.rsi_drop(trading_time) and self.reverse_rsi() and have_units >= 0:
            logger.info(f"Go Long - BUY at ask price: {self.ask}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, (self.units_to_trade + randint(0, 5) * 1000), self.ask, spread, "Go Long - Buy", True, False)

        elif self.bid > self.bb_upper and self.rsi_spike(trading_time) and self.reverse_rsi() and have_units <= 0:
            logger.info(f"Go Short - SELL at bid price: {self.bid}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, - (self.units_to_trade + randint(0, 5) * 1000), self.bid, spread, "Go Short - Sell", True, False)
            
        return
      
    
    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units
        
        if have_units > 0: # long position
            if self.bid > self.price_target and self.reverse_rsi():
                logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}, target: {self.price_target}")
                return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Long - Sell", False, False)

        if have_units < 0: # short position
            if self.ask < self.price_target and self.reverse_rsi():
                logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}, target: {self.price_target}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Short - Buy", False, False)

        # last_trade_time = self.get_last_trade_time()
        # if last_trade_time is not None and (trading_time - last_trade_time) > timedelta(minutes=120):
        #     logger.info(f"Close position - Sell {have_units} units at bid price: {self.bid}, last trade time: {last_trade_time}")
        #     return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Position", False, False)
        
        return None

    def check_for_sl(self, trading_time):

        have_units = self.trading_session.have_units

        if len (self.trading_session.trades) == 0:
            return None

        transaction_price =  self.trading_session.trades[-1][3]
        traded_units = self.trading_session.trades[-1][2]

        if (traded_units == have_units):
            if have_units < 0:
                current_loss_perc = round((self.ask - transaction_price)/transaction_price, 4)
                if current_loss_perc >= (self.sl_perc/2 if (self.risk_time(trading_time) or round(self.units_to_trade/abs(have_units), 1) != 1) else self.sl_perc):
                    logger.info(f"Close short position, - Stop Loss Buy, short price {transaction_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                    return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Short - Buy (SL)", False, True)

            if have_units > 0:
                current_loss_perc = round((transaction_price - self.bid)/transaction_price, 4)
                if current_loss_perc >= (self.sl_perc/2 if (self.risk_time(trading_time) or round(self.units_to_trade/abs(have_units), 1) != 1) else self.sl_perc):
                    logger.info(f"Close long position, - Stop Loss Sell, long price {transaction_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                    return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Long - Sell (SL)", False, True)
        
        return None

