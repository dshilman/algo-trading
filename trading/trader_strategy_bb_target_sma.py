import threading
import json
import logging
import logging.handlers as handlers
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytz
import tpqoa

from trader import Trader
from trader import Trade_Action
from trader import Strategy
from trader import Order

logger = logging.getLogger("trader_oanda")
logger.setLevel(logging.INFO)


class BB_to_SMA_Strategy(Strategy):
    def __init__(self, instrument, SMA, dev):
        super().__init__(instrument,SMA, dev)


    def determine_action(self, bid, ask, units) -> Trade_Action:
        trade_action = None
        signal = 0
        price = None
        spread = ask - bid
        target = None
        instrument = self.instrument

        if units > 0:  # if already have long positions
            logger.debug(f"Have {units} positions, checking if need to close")
            target = self.target + spread
            if bid > target:  # if price is above target SMA, SELL
                signal = -1
                price = bid
                logger.info(
                    f"Signal SELL at price: {round(price, 4)}, sma: {round(self.target, 4)}, spread: {round(spread, 4)}"
                )
        elif units < 0:  # if alredy have short positions
            target = self.target - spread
            if ask < target:  # price is below target SMA, BUY
                signal = 1
                price = ask
                logger.info(
                    f"Signal BUY at price: {round(price, 4)}, sma: {round(self.target, 4)}, spread: {round(spread, 4)}"
                )
        else:  # if no positions
            logger.debug("Don't have any positions, checking if need to open")
            if ask < self.bb_lower:  # if price is below lower BB, BUY
                signal = 1
                price = ask
                logger.info(
                    f"Signal BUY at price: {round(price, 4)}, bb_lower: {round(self.bb_lower, 4)}, spread: {round(spread, 4)}"
                )
            elif bid > self.bb_upper:  # if price is above upper BB, SELL
                signal = -1
                price = bid
                logger.info(
                    f"Signal SELL at price: {round(price, 4)}, bb_upper: {self.bb_upper}, spread: {round(spread, 4)}"
                )
        trade_action = Trade_Action(signal, instrument, price, target, spread)
        logger.debug(trade_action)

        return trade_action

    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units, units_to_trade) -> Order:
        
        order = None

        if trade_action.signal == 0:
            return None

        if sl_perc:
            sl_dist = round(trade_action.price * sl_perc, 4)
        else:
            sl_dist = None

        if tp_perc:
            tp_price = round(
                trade_action.price * (1 + trade_action.signal * tp_perc), 2
            )
        else:
            tp_price = None

        if trade_action.signal == 1:  # if signal is BUY
            logger.info("Signal = BUY")
            if have_units <= 0:  # has short positions
                trade_units = max(units_to_trade, have_units)
                order = Order(
                    trade_action.signal,
                    trade_action.instrument,
                    trade_action.price,
                    trade_units,
                    sl_dist,
                    tp_price,
                )
            else:  # Already have a LONG position
                logger.info(
                    f"Already have {have_units} long positions...skipping trade"
                )
        elif trade_action.signal == -1:  # if signal is SELL
            logger.info("Signal = SELL")
            if have_units >= 0:
                trade_units = min(-units_to_trade, have_units)
                order = Order(
                    trade_action.signal,
                    trade_action.instrument,
                    trade_action.price,
                    trade_units,
                    sl_dist,
                    tp_price,
                )
            else:  # Already have a SHORT position
                logger.info(
                    f"Already have {have_units} short positions...skipping trade"
                )
        logger.debug(order)
        return order


class BB_Strategy_SMA_Target_Trader(Trader):
    def __init__(self, conf_file, instrument, units_to_trade, SMA, dev, sl_perc=None, tp_perc=None, print_trades = False):

        strategy = BB_to_SMA_Strategy(instrument, SMA, dev)

        super().__init__(conf_file, strategy, units_to_trade, sl_perc, tp_perc, print_trades)


if __name__ == "__main__":
    # insert the file path of your config file below!
    days = 1
    stop_after = 10
    print_trades = False
    args = sys.argv[1:]

    if args and len(args) > 0:
        days = int(args[0])

        if args and len(args) > 1:
            stop_after = int(args[1])

            if args and len(args) > 2:
                print_trades = bool(args[2])

    trader = BB_Strategy_SMA_Target_Trader(
        conf_file="oanda.cfg",
        instrument="EUR_USD",
        units_to_trade=10000,
        SMA=100,
        dev=2,
        sl_perc=0.001,
        tp_perc=0.002,
        print_trades = print_trades
    )
    trader.start_trading(days=days, stop_after=stop_after, max_attempts=5)

