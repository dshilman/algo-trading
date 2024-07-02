from trading.utils.errors import PauseTradingException
from trading.strategies.base.strategy_calc import TradingStrategyCalc
from trading.dom.trade import Trade_Action
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

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

        self.cvs = {"USD_CHF": 0.0003, "EUR_USD": 0.0003}
        self.stop_trading = False

    def execute_strategy(self):

        if not self.is_trading:
            logger.debug("Trading is not active")
            return

        trading_time = datetime.now()
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

        trade: Trade_Action = None
        have_units = self.trading_session.have_units

        if have_units != 0:  # if already have positions

            logger.debug(f"Have {have_units} positions, checking for stop loss")
            have_units, trade = self.check_for_sl(trading_time)

            if trade is None:
                logger.debug(f"Have {have_units} positions, checking if need to close a trade")
                trade = self.check_if_need_close_trade(trading_time)

        if trade is None and have_units == 0:  # if already have positions

            logger.debug(f"Have {have_units} positions, checking if need to open a new trade")
            trade = self.check_if_need_open_trade(trading_time)
            
        if trade is not None:
            self.trading_session.add_trade(trade_action=trade, date_time=trading_time)
        
        return trade
            

    def check_if_need_open_trade(self, trading_time):
        pass


    def check_if_need_close_trade(self, trading_time):

        have_units = self.trading_session.have_units

        close_trade = False
        open_trade_time = self.get_last_trade_time()
        open_trade_price = self.get_open_trade_price()

        if open_trade_time is None or (open_trade_time + timedelta(minutes=self.keep_trade_open_time)) <= trading_time or not self.is_trading_time(trading_time):
            close_trade = True

        if have_units > 0:  # long position            
            target_prace = open_trade_price * (1 + self.tp_perc) if open_trade_price is not None else None
            if close_trade or (target_prace is not None and self.bid > target_prace or self.bid > self.price_sma_long) and self.reverse_rsi_down(trading_time):
                if not self.backtest:
                    logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}")
                return Trade_Action(self.instrument, -have_units, self.ask, False, False)

        elif have_units < 0:  # short position
            target_prace = open_trade_price * (1 - self.tp_perc) if open_trade_price is not None else None
            if close_trade or (target_prace is not None and self.ask < target_prace or self.ask < self.price_sma_long) and self.reverse_rsi_up(trading_time):
                if not self.backtest:
                    logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(self.instrument, -have_units, self.bid, False, False)



    def check_for_sl(self, trading_time):

        have_units = self.trading_session.have_units

        if len(self.trading_session.trades) == 0:
            return have_units, None

        open_trade_price = self.get_open_trade_price()

        if have_units < 0:
            current_loss_perc = round((self.ask - open_trade_price)/open_trade_price, 4)
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    have_units = self.api.get_position(self.instrument)
                    self.trading_session.have_units = have_units
                    if have_units == 0:
                        return have_units, None
 
                    logger.info(
                        f"Close short position, - Stop Loss Buy, short price {open_trade_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                return have_units, Trade_Action(self.instrument, -have_units, self.ask, False, True)

        elif have_units > 0:
            current_loss_perc = round((open_trade_price - self.bid)/open_trade_price, 4)
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    have_units = self.api.get_position(self.instrument)
                    self.trading_session.have_units = have_units
                    if have_units == 0:
                        return have_units, None
                
                    logger.info(
                        f"Close long position, - Stop Loss Sell, long price {open_trade_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                return have_units, Trade_Action(self.instrument, -have_units, self.bid, False, True)
        
        return have_units, None
    