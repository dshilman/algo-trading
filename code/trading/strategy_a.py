import configparser
import json
import logging
import sys
from datetime import datetime, time
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
from trading.errors import PauseTradingException
from trading.strategy import TradingStrategy
from trading.tech_indicators import (calculate_momentum, calculate_rsi,
                                     calculate_slope)

logger = logging.getLogger()

class TradingStrategy_A(TradingStrategy):
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)




    def get_target_price(self):

        target = None
        have_units = self.trading_session.have_units

        if have_units != 0 and len (self.trading_session.trades) > 0:
            transaction_price =  self.trading_session.trades[-1][3]
            # traded_units = self.trading_session.trades[-1][2]

            if have_units > 0: # long position
                target = self.bb_upper
       
            elif have_units < 0: # short position
                target = self.bb_lower
        else:
            target = 0

        return target

    
    def check_if_need_close_trade(self):

        have_units = self.trading_session.have_units
        
        if have_units > 0: # long position
            if self.price >= self.price_target and self.reverse_rsi_momentum():
                logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}, target: {self.price_target}")
                return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Long - Sell", False, False)

        if have_units < 0: # short position
            if self.price <= self.price_target and self.reverse_rsi_momentum():
                logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}, target: {self.price_target}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Short - Buy", False, False)

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
                if current_loss_perc >= (self.sl_perc/2 if self.risk_time(trading_time) else self.sl_perc  + 0.001):
                    logger.info(f"Close short position, - Stop Loss Buy, short price {transaction_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                    return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Short - Stop Loss Buy", False, True)

            if have_units > 0:
                current_loss_perc = round((transaction_price - self.bid)/transaction_price, 4)
                if current_loss_perc >= (self.sl_perc/2 if self.risk_time(trading_time) else self.sl_perc  + 0.001):
                    logger.info(f"Close long position, - Stop Loss Sell, long price {transaction_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                    return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Long - Stop Loss Sell", False, True)
        
        return None


    """
        SMA=200
        dev=2
        sl_perc=0.0025
        high_rsi=60
        low_rsi=35
        target=3
    """
    def __str__(self):
        return f"Strategy -- SMA: {self.sma_value}, STD: {self.dev}, stop loss: {self.sl_perc}, rsi high: {self.high_rsi}, rsi low: {self.low_rsi}, target: {self.target}"

    def __repr__(self):
        return f"Strategy -- SMA: {self.sma_value}, STD: {self.dev}, stop loss: {self.sl_perc}, rsi high: {self.high_rsi}, rsi low: {self.low_rsi}, target: {self.target}"
