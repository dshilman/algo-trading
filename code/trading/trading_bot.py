import argparse
import configparser
import logging
import logging.handlers as handlers
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.api.oanda_api import OandaApi
from trading.errors import PauseTradingException
from trading.strategy import TradingStrategy

logger = logging.getLogger()

class Trader():
    def __init__(self, conf_file, pair_file, instrument, unit_test = False):

        self.instrument = instrument
        self.init_logs(unit_test=unit_test)

        self.api = OandaApi(conf_file)


        config = configparser.ConfigParser()  
        config.read(pair_file)

        self.days = int(config.get(self.instrument, 'days'))
        self.start = config.get(self.instrument, 'start')
        self.end = config.get(self.instrument, 'end')

        self.tick_data = []
        self.units = 0

        module = __import__(f"trading.strategies.{instrument.lower()}_strategy", fromlist=[f"{instrument}_Strategy"])
        class_ = getattr(module, f"{instrument}_Strategy")
        self.strategy: TradingStrategy  = class_(instrument=instrument, pair_file=pair_file, api = self.api, unit_test = unit_test)

        today = datetime.utcnow().date()

        self.from_dt = datetime.combine(today, datetime.strptime(self.start, '%H:%M:%S').time())
        self.to_dt = datetime.combine(today, datetime.strptime(self.end, '%H:%M:%S').time())
        if self.to_dt < self.from_dt:
            self.to_dt = self.to_dt + timedelta(days=1)


        super().__init__()


    def init_logs(self, unit_test = False):

        
        if unit_test:
            logger.setLevel(logging.DEBUG)            
        else:
            logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        log_file = os.path.join("../../logs/trading", f"{self.instrument}_{datetime.utcnow().strftime('%m-%d')}_app.log")
        log_handler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)


    def start_trading(self, stop_after = None):

        logger.info("\n" + 100 * "-")
        logger.info ("Started New Trading Session")
        self.terminate = False

        logger.info (f"Getting  candles for: {self.instrument}")
        # self.strategy.data = self.api.get_history_with_all_prices(self.instrument, self.days)
        self.strategy.data = self.api.get_price_candles(pair_name=self.instrument, days=self.days)


        treads = []
        treads.append(threading.Thread(target=self.check_positions, args=(5 * 60,)))
        treads.append(threading.Thread(target=self.check_trading_time, args=(60,)))
        treads.append(threading.Thread(target=self.refresh_strategy, args=(15,)))
        treads.append(threading.Thread(target=self.start_streaming, args=(stop_after,)))

        for t in treads:
            t.start()
            time.sleep(1)
        
        for t in treads:
            t.join()

        self.terminate_session("Finished Trading Session")

    
    def start_streaming(self, stop_after = None):

        i: int = 0

        while not self.terminate:

            try:
                logger.info ("Start Stream")
                # self.api.stream_data(instrument=self.instrument, stop = stop_after, callback=self.new_price_tick)
                self.api.stream_prices(instrument=self.instrument, stop = stop_after, callback=self.new_price_tick)

                self.terminate = True
                break

            except Exception as e:
                logger.error(f"Error in start_streaming")
                logger.exception(e)
                i = i + 1
                if i > 30:
                    self.terminate = True
                    break

    def stop_streaming(self):

        logger.info ("Stop Stream")
        self.api.stop_stream()


    def check_trading_time(self, refresh = 60):

        while not self.terminate:

            logger.debug("Check Trading Time")

            now = datetime.utcnow()
            
            if self.from_dt <= now <= self.to_dt:
                time.sleep(refresh)
            else:
                logger.info(f"Now: {now}, Trading Time: {self.from_dt} - {self.to_dt}")
                logger.info("Not Trading Time - Terminating Trading")
                self.terminate = True
                self.stop_streaming()
                break



    def refresh_strategy(self, refresh = 30):

        i: int = 0

        pause_trading = None

        while not self.terminate:

            logger.debug("Refreshing Strategy")

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
                    logger.debug(f"Resampled Data: {df}")

                self.strategy.calc_indicators(df)
            
                now = datetime.utcnow()
                if pause_trading == None or now > pause_trading:
                    try:
                        self.units = self.strategy.execute_strategy(self.units)
                    except PauseTradingException as e:
                        logger.error(f"Caught Stop Loss Error. Keep Traiding...")
                        # logger.error(f"Pausing Trading for {e.hours} hour(s)")
                        # pause_trading = now + timedelta(hours = e.hours)
                else:
                    logger.info(f"Pausing Trading until: {pause_trading}")

                time.sleep(refresh)

            except Exception as e:
                logger.error("Exception occurred in refresh_strategy")
                logger.exception(e)
                i = i + 1
                if i > 20:
                    self.terminate = True
                    break
                time.sleep(5)


    def check_positions(self, refresh = 300): 

        i: int = 0

        while not self.terminate:
            try:

                logger.debug("Check Positions")

                # self.units = self.api.get_instrument_positions(instrument = self.instrument)
                self.units = self.api.get_position(instrument = self.instrument)

                logger.info(f"Instrument: {self.instrument}, Units: {self.units}")


                time.sleep(refresh)

            except Exception as e:
                logger.error("Exception occurred in check_positions")
                logger.exception(e)
                i = i + 1
                if i > 20:
                    self.terminate = True
                    break
                time.sleep(5)
        
 
    def new_price_tick(self, instrument, time, bid, ask):

        logger.debug(f"{instrument} ----- time: {time}  ---- ask: {ask} ----- bid: {bid}")
         # 2023-12-19T13:28:35.194571445Z
        date_time = pd.to_datetime(time).replace(tzinfo=None)
        
        recent_tick = [date_time, (ask + bid)/2, bid, ask]
        self.tick_data.append(recent_tick)

        minute: int = date_time.minute
        second: int = date_time.second

        if minute in [0, 15, 30, 45] and second == 0:

            logger.info(
                f"Heartbeat --- instrument: {self.instrument}, ask: {round(ask, 4)}, bid: {round(bid, 4)}"
            )
 
  
        
    def terminate_session(self, cause):
        # self.stop_stream = True
        logger.info (cause)

        self.strategy.trading_session.print_trades()


    
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('pair', type=str, help='pair')
    args = parser.parse_args()

    config_file = os.path.abspath(path="../../config/oanda.cfg")
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
