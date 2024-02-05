import json
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import tpqoa

import os
import sys
from pathlib import Path

# file = Path(__file__).resolve()
# parent, root = file.parent, file.parents[1]
# sys.path.append(str(root))

from dom.base import BaseClass
from dom.order import Order

class OANDA_API(BaseClass):
    def __init__(self, conf_file, logger = None):
        super().__init__(logger)
        self.api = tpqoa.tpqoa(conf_file)


    def get_history_with_all_prices(self, instrument, days = 1):
        
        ask_prices: pd.DataFrame = self.get_history(instrument = instrument, price = "A", days = days)
        ask_prices.rename(columns = {"c":"ask"}, inplace = True)
        ask_prices = ask_prices.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

        bid_prices: pd.DataFrame = self.get_history(instrument = instrument, price = "B", days = days)
        bid_prices.rename(columns = {"c":"bid"}, inplace = True)
        bid_prices = bid_prices.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

        df: pd.DataFrame = pd.concat([ask_prices, bid_prices], axis=1)

        df [instrument] = df[['ask', 'bid']].mean(axis=1)

        return df

    def create_order(self, order: Order):

        return self.api.create_order(instrument = order.instrument, units = order.units, sl_distance = order.sl, tp_price=order.tp, suppress=True, ret=True)


    def get_history(self, instrument, price = "M", days = 1):
        
        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = days)
        
        df: pd.DataFrame = pd.DataFrame()

        df_t = self.api.get_history(instrument = instrument, start = past, end = now,
                            granularity = "S30", price = price, localize = True).c.dropna().to_frame()
        df = pd.concat([df, df_t])

        return df

    def stream_data(self, instrument, stop = 10, callback = None):
 
        self.api.stream_data(instrument, stop = stop, ret=False, callback=callback)
 
    def stop_stream(self):
    
            self.api.stop_stream = True
    
    def submit_order(self, order: Order):

        self.log_info(f"Submitting Order: {order}")
        if not self.unit_test:        
            oanda_order = self.api.create_order(instrument = order.instrument, units = order.units, sl_distance = order.sl, tp_price=order.tp, suppress=True, ret=True)
            # self.report_trade(oanda_order)
            if "rejectReason" not in oanda_order:
                self.units = self.units + order.units
                self.log_info(f"New # of {order.instrument} units: {self.units}")
            else:
                error = f"Order was not filled: {oanda_order ['type']}, reason: {oanda_order['rejectReason']}"
                self.log_error(error)
                raise Exception(error)
        else:
            self.units = self.units + order.units
            self.log_info(f"New # of {order.instrument} units: {self.units}")

    
    def report_trade(self, order):

        self.log_info("\n" + 100 * "-" + "\n")
        self.log_info()
        self.log_info("\n" + self.strategy.data[-10:].to_string(header=True))
        self.log_info()
        self.strategy.print_indicators(order.get("price"))
        self.log_info()
        self.log_info(json.dumps(order, indent = 2))
        self.log_info("\n" + 100 * "-" + "\n")


    
    def get_instrument_positions(self, instrument): 

        units = 0
        positions = self.api.get_positions()
        for position in positions:
            instrument = position["instrument"]
            long_units = position["long"]["units"]
            short_units = position["short"]["units"]
            self.log_info (f"Currently have position: {instrument} | long_units: {long_units} | short_units: {short_units}")
            if str(instrument).upper() == instrument:
                units = round(float(long_units) + float(short_units), 0)

        return units

