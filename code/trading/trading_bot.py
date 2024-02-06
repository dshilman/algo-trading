import argparse
import configparser
import logging
import logging.handlers as handlers
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from pathlib import Path
import sys
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))


from trading.api import OANDA_API
from trading.dom.base import BaseClass
from trading.strategy import TradingStrategy

class Trader(BaseClass):
    def __init__(self, conf_file, pair_file, instrument, unit_test = False):

        self.instrument = instrument
        self.init_logs(unit_test=unit_test)

        self.api = OANDA_API(conf_file, logger=self.logger)

        config = configparser.ConfigParser()  
        config.read(pair_file)

        self.days = int(config.get(self.instrument, 'days'))
        self.start = config.get(self.instrument, 'start')
        self.end = config.get(self.instrument, 'end')

        self.tick_data = []
        self.units = 0
            
        self.strategy  = TradingStrategy(instrument=instrument, pair_file=pair_file, api = self.api, logger=self.logger, unit_test = unit_test)

        super().__init__(logger=self.logger)


    def init_logs(self, unit_test = False):

        self.logger = logging.getLogger()

        if unit_test:
            self.logger.setLevel(logging.DEBUG)            
        else:
            self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        log_file = os.path.join("../../logs/trading", f"{self.instrument}_{datetime.utcnow().strftime('%m-%d')}_app.log")
        log_handler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        log_handler.setFormatter(formatter)
        self.logger.addHandler(log_handler)


    def start_trading(self, stop_after = None):

        self.log_info("\n" + 100 * "-")
        self.log_info ("Started New Trading Session")
        self.terminate = False

        self.log_info (f"Getting  candles for: {self.instrument}")
        self.strategy.data = self.api.get_history_with_all_prices(self.instrument, self.days)

        treads = []
        treads.append(threading.Thread(target=self.check_trading_time, args=(60,)))
        treads.append(threading.Thread(target=self.refresh_strategy, args=(30,)))
        treads.append(threading.Thread(target=self.check_positions, args=(5 * 60,)))
        treads.append(threading.Thread(target=self.start_streaming, args=(stop_after,)))

        for t in treads:
            t.start()
        
        for t in treads:
            t.join()

        self.terminate_session("Finished Trading Session")

    
    def start_streaming(self, stop_after = None):

        i: int = 0

        while not self.terminate:

            try:
                self.log_info ("Start Stream")
                self.api.stream_data(instrument=self.instrument, stop = stop_after, callback=self.new_price_tick)
                self.terminate = True
                break

            except Exception as e:
                self.log_error(f"Error in start_streaming")
                self.log_exception(e)
                i = i + 1
                if i > 20:
                    self.terminate = True
                    break

    def stop_streaming(self):

        self.log_info ("Stop Stream")
        self.api.stop_stream()


    def check_trading_time(self, refresh = 60):

        while not self.terminate:

            self.log_debug("Check Trading Time")

            now = datetime.now()
            today = now.date()

            from_dt = datetime.combine(today, datetime.strptime(self.start, '%H:%M:%S').time())
            to_dt = datetime.combine(today, datetime.strptime(self.end, '%H:%M:%S').time())

            if to_dt < from_dt:
                to_dt = to_dt + timedelta(days=1)

            if not from_dt <= now <= to_dt and self.units == 0:
                self.log_info(f"Now: {now}, Trading Time: {from_dt} - {to_dt}")
                self.log_info("Not Trading Time - Terminating Trading")
                self.terminate = True
                self.stop_streaming()
                break

            time.sleep(refresh)


    def refresh_strategy(self, refresh = 60):

        i: int = 0

        while not self.terminate:

            self.log_debug("Refreshing Strategy")

            try:

                temp_tick_data = self.tick_data.copy()
                self.tick_data = []

                df = None

                if len(temp_tick_data) > 0:
                    df = pd.DataFrame(temp_tick_data, columns=["time", self.instrument, "bid", "ask"])
                    df.reset_index(inplace=True)
                    df.set_index('time', inplace=True)    
                    df.drop(columns=['index'], inplace=True)

                    df = df.resample("30s").last()
                    self.log_debug(f"Resampled Data: {df}")

                    # df = df.resample("1Min").last()

                self.units = self.strategy.execute_strategy(self.units, df)

                time.sleep(refresh)

            except Exception as e:
                self.log_error("Exception occurred in refresh_strategy")
                self.log_exception(e)
                i = i + 1
                if i > 20:
                    self.terminate = True
                    break
                time.sleep(5)



    def check_positions(self, refresh = 300): 

        i: int = 0

        while not self.terminate:
            try:

                self.log_debug("Check Positions")

                self.units = self.api.get_instrument_positions(instrument = self.instrument)
                self.log_info(f"Instrument: {self.instrument}, Units: {self.units}")


                time.sleep(refresh)

            except Exception as e:
                self.log_error("Exception occurred in check_positions")
                self.log_exception(e)
                i = i + 1
                if i > 20:
                    self.terminate = True
                    break
                time.sleep(5)
        
 
    def new_price_tick(self, instrument, time, bid, ask):

        self.log_debug(f"{instrument} ----- time: {time}  ---- ask: {ask} ----- bid: {bid}")
         # 2023-12-19T13:28:35.194571445Z
        date_time = pd.to_datetime(time).replace(tzinfo=None)
        
        recent_tick = [date_time, (ask + bid)/2, bid, ask]
        self.tick_data.append(recent_tick)

        minute: int = date_time.minute
        second: int = date_time.second

        if minute in [0, 15, 30, 45] and second == 0:

            self.log_info(
                f"Heartbeat --- instrument: {self.instrument}, ask: {round(ask, 4)}, bid: {round(bid, 4)}"
            )
 
  
        
    def terminate_session(self, cause):
        # self.stop_stream = True
        self.log_info (cause)

        self.strategy.trading_session.print_trades()

        """
            Close the open position, I have observed that trades open from one day to the next
            have incurred a signifucant loss
        """

        """""
        if self.units != 0 and not self.unit_test:
            close_order = self.create_order(self.instrument, units = -self.units, suppress = True, ret = True)
            if not "rejectReason" in close_order:
                self.report_trade(close_order, "Closing Long Position" if self.units > 0 else "Closing Short Position")
                self.units = 0
                trade = [close_order["fullPrice"]["bids"][0]["price"], close_order["fullPrice"]["asks"][0]["price"], self.strategy.sma, self.strategy.bb_lower, self.strategy.bb_upper, float(close_order.get("units")), float(close_order["price"]), self.units]
                self.trades.append(trade)
            else:
                self.log_error(f"Close order was not filled: {close_order ['type']}, reason: {close_order['rejectReason']}")

        """
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('pair', type=str, help='pair')
    args = parser.parse_args()

    config_file = os.path.abspath(os.environ.get("oanda_config", "../../config/oanda_demo.cfg"))
    print (f"oanda config file: {config_file}")
    if os.path.exists(config_file) == False:
        print(f"Config file does not exist: {config_file}")
        exit(1) 
    
    trader = Trader(
        conf_file=config_file,
        pair_file="pairs.ini",
        instrument=args.pair,
        unit_test=False
    )
    trader.start_trading()
    
# python trading_bot.py EUR_USD
