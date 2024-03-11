import configparser
import json
import logging
import sys
from datetime import datetime, timedelta
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

class TradingStrategy_B(TradingStrategy):
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__(instrument=instrument, pair_file=pair_file, api = api, unit_test = unit_test)
        self.num_open_trades = 0
        self.last_trade_time = None

    def determine_trade_action(self, trading_time) -> Trade_Action:

        have_units = self.trading_session.have_units

        if have_units != 0:  # if already have positions
            logger.debug(f"Have {have_units} positions, checking for stop loss")
            trade_action = self.check_for_sl(trading_time)
            if trade_action is not None:
                return trade_action
            
            logger.debug(f"Have {have_units} positions, checking if need to close")
            trade = self.check_if_need_close_trade()

            if trade is not None:
                return trade

        if have_units == 0 or have_units % self.units_to_trade <= 3:

            if have_units != 0:
                last_tran_time = self.get_last_trade_time()
                if last_tran_time is not None and (last_tran_time + timedelta(minutes=5)) > trading_time:
                    return None

            logger.debug(f"Have {have_units} positions, checking if need to open")
            trade = self.check_if_need_open_trade(trading_time)
            if trade is not None:
                return trade

        return None
    
    
    def has_high_rsi(self, trading_time):

        if self.risk_time(trading_time) or self.rsi_max - self.rsi >= 10:
            return self.rsi > 70
        elif self.trading_session.have_units < 0:
            return self.rsi > self.high_rsi + 5
        else:
            return self.rsi_max > self.high_rsi
        
        # return self.rsi_max > (self.high_rsi if not self.risk_time(trading_time) else 70)
    
    def has_low_rsi(self, trading_time):
        
        if self.risk_time(trading_time) or self.rsi_max - self.rsi >= 10:
            return self.rsi < 30
        elif self.trading_session.have_units > 0:
            return self.rsi < self.low_rsi - 5
        else:
            return self.rsi_min < self.low_rsi
        # return self.rsi_min < (self.low_rsi if not self.risk_time(trading_time) else 30)
    
    def get_last_trade_time(self):

        date_time = None
        
        if len(self.trading_session.trades) > 0:
            date_time_s = self.trading_session.trades[-1][0]
            date_time = datetime.strptime(date_time_s, "%m/%d/%Y %H:%M:%S").replace(tzinfo=None)
        
        return date_time
