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

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategyBase():
    def __init__(self, trading_strategy, pair_file, api = None, unit_test = False):
        super().__init__()

        self.api:OandaApi = api
        self.unit_test = unit_test
        self.backtest = False


        config = configparser.ConfigParser()  
        config.read(pair_file)
        self.instrument = config.get(trading_strategy, "pair")
        self.SMA = config.getint(trading_strategy, 'SMA')
        self.DEV = config.getfloat(trading_strategy, 'dev')
        self.trading_volume = config.getint(trading_strategy, 'trading_volume')
        self.trading_std = config.getfloat(trading_strategy, 'trading_std')
        # self.rsi_high = float(config.get(trading_strategy, 'rsi_high'))
        # self.rsi_low = float(config.get(trading_strategy, 'rsi_low'))
        self.rsi_change = config.getfloat(trading_strategy, 'rsi_change')
        self.units_to_trade = config.getint(trading_strategy, 'units_to_trade')
        self.sl_perc = config.getfloat(trading_strategy, 'sl_perc')
        self.tp_perc = config.getfloat(trading_strategy, 'tp_perc')
        self.pause_start = config.get(trading_strategy, 'pause_start')
        self.pause_end = config.get(trading_strategy, 'pause_end')
        self.short_trading = config.getboolean(trading_strategy, 'short_trading')
        self.long_trading = config.getboolean(trading_strategy, 'long_trading')
        self.keep_trade_open_time = config.getint(trading_strategy, 'keep_trade_open_time')
        self.data: pd.DataFrame = None

        self.trading_session = Trading_Session(self.instrument)


    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc) -> Order:
        
        tp_price = None
        sl_price = None

        if trade_action.open_trade:
            
            """
                Have been getting STOP_LOSS_ON_FILL_DISTANCE_PRECISION_EXCEEDED when trading GBP_JPY
                I assume that the price is too high for 4 digit decimals, thus adding a rule
                if the price is grater that $100, do not use decimals for stop loss
            """

            # sl_dist = round(trade_action.price * (sl_perc), (4 if trade_action.price < 100 else 0))
            sl_price = round(trade_action.price - (1 if trade_action.units > 0 else -1) * trade_action.price * (sl_perc + .001), (4 if trade_action.price < 100 else 0))

                
            if tp_perc:
                tp_price = round(trade_action.price + (1 if trade_action.units > 0 else -1) * trade_action.price * (tp_perc + .001), (4 if trade_action.price < 100 else 0))


        order = Order(
            instrument = trade_action.trading_strategy,
            price = trade_action.price,
            trade_units = trade_action.units,
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

    def report_trade(self, order):

        logger.info("\n" + 100 * "-" + "\n")
        logger.info("")
        logger.info("\n" + self.data[-8:].to_string(header=True))
        logger.info("")
        logger.info(json.dumps(order, indent=2))
        logger.info("\n" + 100 * "-" + "\n")

    def terminate(self):

        self.trading_session.print_trades()


    def __str__(self):
        return f"Strategy -- SMA: {self.SMA}, STD: {self.DEV}, stop loss: {self.sl_perc}"

    def __repr__(self):
        return f"Strategy -- SMA: {self.SMA}, STD: {self.DEV}, stop loss: {self.sl_perc}"
