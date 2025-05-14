from math import log
from trading.strategies.base.strategy_calc import TradingStrategyCalc
from trading.dom.trade import Trade_Action
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from pathlib import Path

import pandas as pd
from tabulate import tabulate
import pytz

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))


logger = logging.getLogger()


class TradingStrategyExec(TradingStrategyCalc):
    def __init__(self, trading_strategy, pair_file, api = None, unit_test=False):

        super().__init__(trading_strategy=trading_strategy, pair_file=pair_file, api=api, unit_test=unit_test)


    def execute_strategy(self, trading_time):
       
        trade_action: Trade_Action = self.determine_trade_action(trading_time)

        if trade_action is not None:
            logger.info(f"{trade_action}")
            order = self.create_order(trade_action)
            self.submit_order(order)
        else:
            logger.debug("No trade action")

        # if trade_action is not None and trade_action.sl_trade:
        #     raise PauseTradingException(2)

        return

    def determine_trade_action(self, trading_time) -> Trade_Action:

        have_units = self.trading_session.have_units

        spread = round((self.ask - self.bid), 5)
        is_trading_time = self.is_trading_time(trading_time)

        if not self.backtest:
            logger.info(f"is trading: {is_trading_time}, have_unit: {have_units}, spread: {spread}, trading spread: {self.trading_spread}")

        trade = None
        
        if have_units == 0 and is_trading_time and (self.trading_spread == 0 or spread <= self.trading_spread):
      
            logger.debug(f"Have {have_units} positions, checking if need to open a new trade")
            trade = self.check_if_need_open_trade(trading_time)

        elif abs(have_units) == self.units_to_trade:

            logger.debug(f"Have {have_units} positions, checking for stop loss")
            trade = self.check_for_sl(trading_time, have_units)

            if trade is None:
                logger.debug(f"Have {have_units} positions, checking if need to close a trade")
                trade = self.check_if_need_close_trade(trading_time)
           
        if trade is not None:            
            self.trading_session.add_trade(trade_action=trade, date_time=trading_time)
        
        return trade # type: ignore
            

    def check_if_need_open_trade(self, trading_time) -> Trade_Action:
        # Implement the logic to determine if a new trade needs to be opened
        # For now, return a default Trade_Action or raise an exception
        raise NotImplementedError("This method needs to be implemented")


    def check_for_sl(self, trading_time, have_units) -> Trade_Action:

        base_price = None
        
        open_trade_price = self.get_open_trade_price()
        
        if open_trade_price is None:
            return None # type: ignore
        
        if have_units < 0:
            if self.trailing_sl:
                base_price = min(self.price_low, open_trade_price)
            else: 
                base_price = open_trade_price
             
            current_loss_perc = (self.ask - base_price)/base_price
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    logger.info(
                        f"Close short position, - Stop Loss Buy, short price {base_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                return Trade_Action(trading_time, self.instrument, -have_units, self.ask, False, True, False)

        elif have_units > 0:
            if self.trailing_sl:
                base_price = max(self.price_high, open_trade_price)
            else: 
                base_price = open_trade_price

            current_loss_perc = (base_price - self.bid)/base_price
            if current_loss_perc >= self.sl_perc:
                if not self.backtest:
                    logger.info(
                        f"Close long position, - Stop Loss Sell, long price {base_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                return Trade_Action(trading_time, self.instrument, -have_units, self.bid, False, True, False)
        
        return None # type: ignore
    
    def calc_open_trade_profit(self, units) -> float:

        open_trade_price = self.get_open_trade_price()

        if units < 0:
            return (self.price - open_trade_price) / open_trade_price
        elif units > 0:
            return (self.price - open_trade_price) / open_trade_price
        
        return 0


    def need_close_trade(self, trading_time) -> bool:

        if not self.is_trading_time(trading_time):
            return True

        # if self.calc_trade_open_duration(trading_time) > 240 and round(self.calc_open_trade_profit(self.trading_session.have_units), 4) <= 0:
        #     return True

        open_trade_time = self.get_open_trade_time()        

        if open_trade_time is not None and (open_trade_time + timedelta(minutes=self.keep_trade_open_time, seconds=-open_trade_time.second)) <= trading_time:
            return True

        return False
    
    def calc_trade_open_duration(self, trading_time: pd.Timestamp) -> int:

        open_trade_time = self.get_open_trade_time()
        return 0 if open_trade_time is None else int((trading_time - open_trade_time).total_seconds() // 60)

    def get_open_trade_price(self) -> float: # type: ignore

        trade: Trade_Action = self.get_open_trade()
        if trade and trade.open_trade:
            return trade.price

       
    def get_open_trade(self) -> Trade_Action:

        have_units = self.trading_session.have_units

        if have_units != 0 and len(self.trading_session.trades) > 0:
            trade = self.trading_session.trades[-1]
            if trade[2].startswith("Open"):
                # ["datetime", "trade_id", "trade", "action", "units", "price", "trade_pl", "trade_pl_pct", "pl"]
                return Trade_Action(time=trade[0], instrument=self.instrument, units=trade[4], open_trade=True, price=trade[5])
        
        return None # type: ignore


    def is_trading_time(self, date_time: datetime) -> bool:
        logger.debug(f"Date time (UTC): {date_time}")

        # Convert UTC to EST
        est = pytz.timezone('US/Eastern')
        date_time_est = date_time.astimezone(est)
        logger.debug(f"Date time (EST): {date_time_est}")

        # day = date_time_est.weekday()
        # hour = date_time_est.hour

        # if day == 4 and hour >= 20:
        #     return False

        pause_from_dt = datetime.combine(date_time_est.date(), datetime.strptime(self.pause_start_est, '%H:%M:%S').time(), tzinfo=est)
        pause_to_dt = datetime.combine(date_time_est.date(), datetime.strptime(self.pause_end_est, '%H:%M:%S').time(), tzinfo=est)

        if pause_from_dt > pause_to_dt:
            pause_from_dt = pause_from_dt - pd.DateOffset(days=1)

        if pause_from_dt <= date_time_est < pause_to_dt:
            return False

        return True

    def get_open_trade_time(self) -> pd.Timestamp: # type: ignore

        trade: Trade_Action = self.get_open_trade()
        if trade and trade.open_trade:
            return trade.time

    def take_profit(self):

        tp = False
        tp_price = 0

        have_units = self.trading_session.have_units
        open_trade_price = self.get_open_trade_price()

        if have_units > 0 and open_trade_price is not None:  # long position
            target_price = open_trade_price * (1 + self.tp_perc)
            tp = self.price_high > target_price
            tp_price = target_price
        elif have_units < 0 and open_trade_price is not None:  # short position
            target_price = open_trade_price * (1 - self.tp_perc)
            tp = self.price_low < target_price
            tp_price = target_price
        
        return tp, tp_price
    
    def check_if_need_close_trade(self, trading_time) -> Trade_Action: # type: ignore

        have_units = self.trading_session.have_units
        close_trade = self.need_close_trade(trading_time)
        take_profit, tp_price = self.take_profit()

        if have_units > 0:  # long position
            if (close_trade or take_profit) and self.is_up:
                if not self.backtest:
                    logger.info(f"Close long position  - Sell {have_units} units at ask price: {self.bid}")
                return Trade_Action(trading_time, self.instrument, -have_units, tp_price if take_profit else self.bid, False, False, take_profit)
                
        elif have_units < 0:  # short position
            if (close_trade or take_profit) and not self.is_up:

                if not self.backtest:
                   logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}")
                return Trade_Action(trading_time, self.instrument, -have_units, tp_price if take_profit else self.ask, False, False, take_profit)

