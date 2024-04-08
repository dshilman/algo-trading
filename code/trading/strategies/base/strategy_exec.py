from trading.utils.tech_indicators import (calculate_momentum, calculate_rsi,
                                           calculate_slope)
from trading.utils.errors import PauseTradingException
from trading.strategies.base.strategy_calc import TradingStrategyCalc
from trading.dom.trading_session import Trading_Session
from trading.dom.trade import Trade_Action
from trading.dom.order import Order
from trading.api.oanda_api import OandaApi
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


logger = logging.getLogger()


class TradingStrategyExec(TradingStrategyCalc):
    def __init__(self, instrument, pair_file, api=None, unit_test=False):
        super().__init__(instrument=instrument,
                         pair_file=pair_file, api=api, unit_test=unit_test)

    def execute_strategy(self):

        trading_time = datetime.utcnow()
        trade_action = self.determine_trade_action(trading_time)

        if trade_action is not None:
            # logger.info(f"trade_action: {trade_action}")

            order = self.create_order(trade_action, self.sl_perc, self.tp_perc)

            if order is not None:
                self.submit_order(order)
                self.trading_session.add_trade(trade_action=trade_action)

        if trade_action is not None and trade_action.sl_trade:
            raise PauseTradingException(2)

        return

    def determine_trade_action(self, trading_time) -> Trade_Action:

        have_units = self.trading_session.have_units

        if have_units != 0:  # if already have positions
            logger.debug(
                f"Have {have_units} positions, checking if need to close")
            trade = self.check_if_need_close_trade(trading_time)
            if trade is not None:
                return trade
        else:
            # if have_units == 0 or (abs(have_units / self.units_to_trade) < 2 and not self.is_too_soon(trading_time)):
            logger.debug(
                f"Have {have_units} positions, checking if need to open")
            trade = self.check_if_need_open_trade(trading_time)
            if trade is not None:
                # self.reset_rsi()
                return trade

        if have_units != 0:  # if already have positions
            logger.debug(
                f"Have {have_units} positions, checking for stop loss")
            trade_action = self.check_for_sl(trading_time)
            if trade_action is not None:
                return trade_action

        return None

    def check_if_need_open_trade(self, trading_time):

        if self.risk_time(trading_time):
            return

        spread = round(self.ask - self.bid, 4)

        if self.long_trading and self.rsi_drop() and self.reverse_rsi_up_open():
            if not self.backtest:
                logger.info(
                    f"Go Long - BUY at ask price: {self.ask}, bb low: {self.bb_low}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, self.units_to_trade, self.ask, spread, "Go Long - Buy", True, False)

        elif self.short_trading and self.rsi_spike() and self.reverse_rsi_down_open():
            if not self.backtest:
                logger.info(
                    f"Go Short - SELL at bid price: {self.bid}, bb high: {self.bb_high}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, -self.units_to_trade, self.bid, spread, "Go Short - Sell", True, False)

        return

    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_last_trade_time()
        open_trade_rsi = self.get_open_trade_rsi()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time or self.risk_time(trading_time):
            close_trade = True

        if have_units > 0:  # long position
            if close_trade or (open_trade_rsi is not None and self.rsi_prev < open_trade_rsi + self.rsi_change) and self.reverse_rsi_down_close():
                if not self.backtest:
                    logger.info(
                        f"Close long position - Sell {-have_units} units at bid price: {self.bid}")
                return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Long - Sell", False, False)

        if have_units < 0:  # short position
            if close_trade or (open_trade_rsi is not None and self.rsi_prev < open_trade_rsi - self.rsi_change) and self.reverse_rsi_up_close():
                if not self.backtest:
                    logger.info(
                        f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Short - Buy", False, False)

        return None

    def check_for_sl(self, trading_time):

        have_units = self.trading_session.have_units

        if len(self.trading_session.trades) == 0:
            return None

        open_trade_price = self.get_open_trade_price()

        if have_units < 0:
            # sl_price = transaction_price + 2 * (self.ask - self.bid)
            # if self.ask > sl_price:
            #     return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Short - Buy (SL)", False, True)

            current_loss_perc = round(
                (self.ask - open_trade_price)/open_trade_price, 4)
            if current_loss_perc >= (self.sl_perc/2 if self.risk_time(trading_time) else self.sl_perc):
                if not self.backtest:
                    logger.info(
                        f"Close short position, - Stop Loss Buy, short price {open_trade_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Short - Buy (SL)", False, True)

        if have_units > 0:

            # sl_price = transaction_price - 2 * (self.ask - self.bid)
            # if self.bid < sl_price:
            #     return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Long - Sell (SL)", False, True)

            current_loss_perc = round((open_trade_price - self.bid)/open_trade_price, 4)
            if current_loss_perc >= (self.sl_perc/2 if self.risk_time(trading_time) else self.sl_perc):
                if not self.backtest:
                    logger.info(
                        f"Close long position, - Stop Loss Sell, long price {open_trade_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Long - Sell (SL)", False, True)

        return None

    def report_trade(self, order):

        logger.info("\n" + 100 * "-" + "\n")
        logger.info("")
        logger.info("\n" + self.data[-8:].to_string(header=True))
        logger.info("")
        self.print_indicators()
        logger.info("")
        logger.info(json.dumps(order, indent=2))
        logger.info("\n" + 100 * "-" + "\n")

    def terminate(self):

        # add terminate logic here
        self.trading_session.print_trades()
