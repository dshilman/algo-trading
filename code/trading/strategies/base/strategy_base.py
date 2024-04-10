import configparser
import json
import logging
import sys
from pathlib import Path

import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.api.oanda_api import OandaApi
from trading.dom.order import Order
from trading.dom.trade import Trade_Action
from trading.dom.trading_session import Trading_Session
from trading.utils.tech_indicators import (calculate_momentum, calculate_rsi,
                                     calculate_slope)

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategyBase():
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__()

        self.trading_session = Trading_Session(instrument)

        self.instrument = instrument
        self.api:OandaApi = api
        self.unit_test = unit_test
        self.backtest = False


        config = configparser.ConfigParser()  
        config.read(pair_file)
        self.SMA = config.getint(instrument, 'SMA')
        self.DEV = config.getfloat(instrument, 'dev')
        # self.rsi_high = float(config.get(instrument, 'rsi_high'))
        # self.rsi_low = float(config.get(instrument, 'rsi_low'))
        self.rsi_change = config.getfloat(instrument, 'rsi_change')
        self.units_to_trade = config.getint(instrument, 'units_to_trade')
        self.sl_perc = config.getfloat(self.instrument, 'sl_perc')
        self.tp_perc = config.getfloat(self.instrument, 'tp_perc')
        self.pause_start = config.get(self.instrument, 'pause_start')
        self.pause_end = config.get(self.instrument, 'pause_end')
        self.short_trading = config.getboolean(self.instrument, 'short_trading')
        self.long_trading = config.getboolean(self.instrument, 'long_trading')
        self.keep_trade_open_time = config.getint(instrument, 'keep_trade_open_time')
        self.data: pd.DataFrame = None
  
        self.rsi_min_date = None
        self.rsi_max_date = None

    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc) -> Order:
        
        tp_price = None
        sl_price = None

        # if trade_action.open_trade:
        if trade_action.spread / trade_action.price >= sl_perc:
            logger.warning(f"Current spread: {trade_action.spread} is too large for price: {trade_action.price} and sl_perc: {sl_perc}")
            return None
        if trade_action.open_trade:
            
            """
                Have been getting STOP_LOSS_ON_FILL_DISTANCE_PRECISION_EXCEEDED when trading GBP_JPY
                I assume that the price is too high for 4 digit decimals, thus adding a rule
                if the price is grater that $100, do not use decimals for stop loss
            """

            # sl_dist = round(trade_action.price * (sl_perc), (4 if trade_action.price < 100 else 0))
            sl_price = round(trade_action.price - (1 if trade_action.units > 0 else -1) * trade_action.price * (sl_perc + .0005), (4 if trade_action.price < 100 else 0))

                
            if tp_perc:
                tp_price = round(trade_action.price + (1 if trade_action.units > 0 else -1) * trade_action.price * (tp_perc + .0005), (4 if trade_action.price < 100 else 0))


        order = Order(
            instrument = trade_action.instrument,
            price = trade_action.price,
            trade_units = trade_action.units,
            # sl_dist = sl_dist,
            sl_price = sl_price,
            tp_price = tp_price
        )
        logger.debug(order)

        return order


    def submit_order(self, order: Order):

        logger.info(f"Submitting Order: {order}")
        if not self.unit_test:        
            # result = self.api.create_order(order=order)
            result = self.api.place_order(order=order)
            self.report_trade(result)
            if "rejectReason" in result:               
                error = f"Order was not filled: {result ['type']}, reason: {result['rejectReason']}"
                logger.error(error)
                raise Exception(error)
        
        return

    def __str__(self):
        return f"Strategy -- SMA: {self.SMA}, STD: {self.DEV}, stop loss: {self.sl_perc}"

    def __repr__(self):
        return f"Strategy -- SMA: {self.SMA}, STD: {self.DEV}, stop loss: {self.sl_perc}"
