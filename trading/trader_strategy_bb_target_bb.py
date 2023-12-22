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

logger = logging.getLogger("trader_oanda")
logger.setLevel(logging.INFO)


class BB_Strategy_BB_Target_Trader(Trader):
    def __init__(
        self,
        conf_file,
        instrument,
        bar_length,
        units_to_trade,
        SMA,
        dev,
        sl_perc=None,
        tsl_perc=None,
        tp_perc=None,
    ):
        super().__init__(
            conf_file,
            instrument,
            bar_length,
            units_to_trade,
            SMA,
            dev,
            sl_perc,
            tsl_perc,
            tp_perc,
        )

    def define_strategy(self, resampled_tick_data=None):  # "strategy-specific"
        super().define_strategy(resampled_tick_data)
        self.data["distance"] = self.data[self.instrument] - self.data.Lower

        logger.debug("After defining strategy")
        logger.debug(self.data)

        return

    def determine_action(self, bid, ask):
        # logger.debug ("Inside determine_action")

        signal = 0
        price = None

        # update the latest position

        if ask < self.bb_lower:
            signal = 1
            price = ask
            logger.info(
                f"Signal BUY at price: {price}, bb_lower: {self.bb_lower}, spread: {round(bid - ask, 4)}"
            )

        elif bid > self.bb_upper:
            signal = -1
            price = bid
            logger.info(
                f"Signal SELL at price: {price}, bb_upper: {self.bb_upper}, spread: {round(bid - ask, 4)}"
            )

        else:
            signal = 0
            price = (bid + ask) / 2

        if self.ticks % 100 == 0:
            logger.info(
                f"Heartbeat current tick {self.ticks} --- instrument: {self.instrument}, ask: {round(ask,4)}, bid: {round(bid, 4)}, spread: {round(bid - ask, 4)}, signal: {signal}"
            )

        # if df.distance.iloc[-1] * df.distance.iloc[-2] < 0:
        #     pos = 0

        # df["position"].iloc[-1] = pos

        return signal, price
        

    def execute_trades(self, signal, price):

        if signal == 0:
            return

        current_price = price

        if self.sl_perc:
            sl_dist = round(current_price * self.sl_perc, 4)
        else:
            sl_dist = None

        if self.tsl_perc:
            tsl_dist = round(current_price * self.tsl_perc, 4)
        else:
            tsl_dist = None

        if self.tp_perc:
            tp_price = round(current_price * (1 + signal * self.tp_perc), 2)
        else:
            tp_price = None

        # tp_price = round(self.target, 4)

        if signal == 1:  # if signal is BUY
            logger.info("Signal = BUY")
            if self.position == 0:
                logger.info("No current possitions")
                order = self.create_order(
                    self.instrument,
                    self.units_to_trade,
                    suppress=True,
                    ret=True,
                    sl_distance=sl_dist,
                    tsl_distance=tsl_dist,
                    tp_price=tp_price,
                )
                self.report_trade(order, "GOING LONG")
            elif self.position == -1:
                logger.info(f"Already have {self.units} short positions")
                order = self.create_order(
                    self.instrument,
                    self.units_to_trade * 2,
                    suppress=True,
                    ret=True,
                    sl_distance=sl_dist,
                    tsl_distance=tsl_dist,
                    tp_price=tp_price,
                )
                self.report_trade(order, "GOING LONG")
            elif self.position == 1:
                logger.info(
                    f"Already have {self.units} long positions...skipping trade"
                )
            self.position = 1
        elif signal == -1:
            logger.info("Signal = SELL")
            if self.position == 0:
                logger.info("No current possitions")
                order = self.create_order(
                    self.instrument,
                    -self.units_to_trade,
                    suppress=True,
                    ret=True,
                    sl_distance=sl_dist,
                    tsl_distance=tsl_dist,
                    tp_price=tp_price,
                )
                self.report_trade(order, "GOING SHORT")
            elif self.position == 1:
                logger.info(f"Already have {self.units} long positions")
                order = self.create_order(
                    self.instrument,
                    -self.units_to_trade * 2,
                    suppress=True,
                    ret=True,
                    sl_distance=sl_dist,
                    tsl_distance=tsl_dist,
                    tp_price=tp_price,
                )
                self.report_trade(order, "GOING SHORT")
            elif self.position == -1:
                logger.info(
                    f"Already have {self.units} short positions...skipping trade"
                )

            self.position = -1
        elif signal == 0:
            logger.info("Signal = Neutral - Do nothing")

        signal = 0

        return


if __name__ == "__main__":
    print("Starting BB Strategy Trader")
    # insert the file path of your config file below!
    days = 1
    stop_after = 10
    args = sys.argv[1:]

    if args and len(args) == 2:
        days = int(args[0])
        stop_after = int(args[1])

    print("Initializing BB Strategy Trader")
    trader = BB_Strategy_BB_Target_Trader(
        conf_file="oanda.cfg",
        instrument="EUR_USD",
        bar_length=1,
        units_to_trade=10000,
        SMA=100,
        dev=2,
        sl_perc=0.0002,
        tp_perc=0.0004,
    )
    print("Start Trading")
    trader.start_trading(days=days, stop_after=stop_after, max_attempts=5)
