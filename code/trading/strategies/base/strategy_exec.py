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

        self.stop_trading = False

    def execute_strategy(self):

        if not self.is_trading:
            logger.debug("Trading is not active")
            return

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

        if have_units != 0:  # if already have positions

            logger.debug(f"Have {have_units} positions, checking if need to close a trade")
            trade = self.check_if_need_close_trade(trading_time)
            
            if trade is None:
                logger.debug(f"Have {have_units} positions, checking for stop loss")
                trade = self.check_for_sl(trading_time)
        
        else:
            logger.debug(f"Have {have_units} positions, checking if need to open a new trade")
            trade = self.check_if_need_open_trade(trading_time)
            
        if trade is not None:
            self.trading_session.add_trade(trade_action=trade, date_time=trading_time, rsi=self.rsi)
        
        return trade
            

    def check_if_need_open_trade(self, trading_time):


        if not self.is_trading_time(trading_time) or self.stop_trading:
            return

        if self.long_trading and self.bid <= self.bb_low and self.rsi_drop() and 35 >= round(self.rsi_min, 0) \
                    and self.std > self.std_mean \
                        and self.reverse_rsi_up(trading_time):
                            if not self.backtest:
                                logger.info(
                                    f"Go Long - BUY at ask price: {self.ask}, bb low: {self.bb_low}, rsi: {self.rsi}")
                            return Trade_Action(self.instrument, self.units_to_trade, self.ask, True, False)

        elif self.short_trading and self.ask >= self.bb_high and self.rsi_spike() and 65 <= round(self.rsi_max, 0) \
                    and self.std > self.std_mean \
                        and self.reverse_rsi_down(trading_time):
                            if not self.backtest:
                                logger.info(
                                    f"Go Short - SELL at bid price: {self.bid}, bb high: {self.bb_high}, rsi: {self.rsi}")
                            return Trade_Action(self.instrument, -self.units_to_trade, self.bid, True, False)


    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_last_trade_time()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time:
            close_trade = True

        if have_units > 0:  # long position
            if close_trade or (self.bid > self.sma or self.rsi > 55) and self.reverse_rsi_down(trading_time):
                if not self.backtest:
                    logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}")
                return Trade_Action(self.instrument, -have_units, self.ask, False, False)

        elif have_units < 0:  # short position
            if close_trade or (self.ask < self.sma or self.rsi < 45) and self.reverse_rsi_up(trading_time):
                if not self.backtest:
                    logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, False)



    def check_for_sl(self, trading_time):

        have_units = self.trading_session.have_units

        if len(self.trading_session.trades) == 0:
            return None

        open_trade_price = self.get_open_trade_price()

        if have_units < 0:
            current_loss_perc = round((self.ask - open_trade_price)/open_trade_price, 4)
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    logger.info(
                        f"Close short position, - Stop Loss Buy, short price {open_trade_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.ask, False, True)

        elif have_units > 0:
            current_loss_perc = round((open_trade_price - self.bid)/open_trade_price, 4)
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    logger.info(
                        f"Close long position, - Stop Loss Sell, long price {open_trade_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, True)
        