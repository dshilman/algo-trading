from trading.utils.errors import PauseTradingException
from trading.strategies.base.strategy_calc import TradingStrategyCalc
from trading.dom.trade import Trade_Action
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

        if trade_action is not None and trade_action.sl_trade:
            raise PauseTradingException(2)

        return

    def determine_trade_action(self, trading_time) -> Trade_Action:

        trade = None
        have_units = self.trading_session.have_units

        try:
            if have_units != 0:  # if already have positions

                logger.debug(f"Have {have_units} positions, checking if need to close a trade")
                trade = self.check_if_need_close_trade(trading_time)
                if trade is not None:
                    return trade

                logger.debug(f"Have {have_units} positions, checking for stop loss")
                trade_action = self.check_for_sl(trading_time)
                if trade_action is not None:
                    return trade_action

            else:
                logger.debug(f"Have {have_units} positions, checking if need to open a new trade")
                trade = self.check_if_need_open_trade(trading_time)
                if trade is not None:
                    self.reset_rsi()
                    return trade
             
        finally:
            if trade is not None:
                self.trading_session.add_trade(trade_action=trade, date_time=trading_time, rsi=self.rsi_prev)
            

    def check_if_need_open_trade(self, trading_time):

        if self.risk_time(trading_time):
            return

        spread = round(self.ask - self.bid, 4)

# --------Open Long Trade ------------------------------------------------------------------------------------------------------
        if self.long_trading and self.ask < self.bb_low and self.rsi_drop() and round(self.rsi_prev, 0) <= 35 and self.reverse_rsi_up_open():
            if not self.backtest:
                logger.info(
                    f"Go Long - BUY at ask price: {self.ask}, bb low: {self.bb_low}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, self.units_to_trade, self.ask, spread, "Go Long - Buy", True, False)

# -------- Open Short Trade ------------------------------------------------------------------------------------------------------
        elif self.short_trading and self.bid > self.bb_high and self.rsi_spike() and round(self.rsi_prev, 0) >= 65 and self.reverse_rsi_down_open():
            if not self.backtest:
                logger.info(
                    f"Go Short - SELL at bid price: {self.bid}, bb high: {self.bb_high}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, -self.units_to_trade, self.bid, spread, "Go Short - Sell", True, False)

# --------------------------------------------------------------------------------------------------------------


    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_last_trade_time()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time or self.risk_time(trading_time):
            close_trade = True

# --------- Close Long Trade -----------------------------------------------------------------------------------------------------
        if have_units > 0:  # long position
            if close_trade or (round(self.rsi_prev, 0) >= 65) and self.reverse_rsi_down_close():
                if not self.backtest:
                    logger.info(
                        f"Close long position - Sell {-have_units} units at bid price: {self.bid}")
                return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Long - Sell", False, False)

# ------------ Close Short Trade --------------------------------------------------------------------------------------------------
        elif have_units < 0:  # short position
            if close_trade or (round(self.rsi_prev, 0) <= 35) and self.reverse_rsi_up_close():
                if not self.backtest:
                    logger.info(
                        f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Short - Buy", False, False)

# --------------------------------------------------------------------------------------------------------------


    def check_for_sl(self, trading_time):

        have_units = self.trading_session.have_units

        if len(self.trading_session.trades) == 0:
            return None

        open_trade_price = self.get_open_trade_price()

# -------- Stop Loss for Short Trade ------------------------------------------------------------------------------------------------------
        if have_units < 0:
            current_loss_perc = round((self.ask - open_trade_price)/open_trade_price, 4)
            if current_loss_perc >= (self.sl_perc/2 if self.risk_time(trading_time) else self.sl_perc):
                if not self.backtest:
                    logger.info(
                        f"Close short position, - Stop Loss Buy, short price {open_trade_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Short - Buy (SL)", False, True)

# ---------- Stop Loss for Long Trade ----------------------------------------------------------------------------------------------------
        elif have_units > 0:
            current_loss_perc = round((open_trade_price - self.bid)/open_trade_price, 4)
            if current_loss_perc >= (self.sl_perc/2 if self.risk_time(trading_time) else self.sl_perc):
                if not self.backtest:
                    logger.info(
                        f"Close long position, - Stop Loss Sell, long price {open_trade_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Long - Sell (SL)", False, True)

# --------------------------------------------------------------------------------------------------------------


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
