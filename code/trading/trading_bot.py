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
from trading.utils.errors import PauseTradingException
from trading.strategies.base.strategy_exec import TradingStrategyExec


logger = logging.getLogger()

class Trader():
    def __init__(self, conf_file, pair_file, instrument, unit_test = False):

        self.instrument = instrument
        self.init_logs(unit_test=unit_test)

        self.api = OandaApi(conf_file)


        config = configparser.ConfigParser()  
        config.read(pair_file)

        self.days = int(config.get(self.instrument, 'days'))
        # self.start = config.get(self.instrument, 'start')
        # self.end = config.get(self.instrument, 'end')

        self.tick_data = []
        self.stop_loss_count = 0
        
        class_ = None
        strategy = config.get(instrument, 'strategy')

        try:
            modules = strategy.split(sep=".", maxsplit=2)
            logger.info(f"Loading:{modules[0]} strategy")
            module = __import__(f"trading.strategies.{modules[0]}", fromlist=[f"{modules[1]}"])
            logger.info(f"Loading:{modules[1]} class")
            class_ = getattr(module, modules[1])
        except Exception as e:            
            logger.error(f"Strategy not found for {instrument}", e)
            raise Exception(f"Strategy not found for {instrument}")

        logger.info(f"Running:{class_} strategy")
        self.strategy: TradingStrategyExec  = class_(instrument=self.instrument, pair_file=pair_file, api = self.api, unit_test = unit_test)
        logger.info(f"Trading Strategy: {self.strategy}")

        today = datetime.now(tz=timezone.utc).date()

        # self.from_dt = datetime.combine(today, datetime.strptime(self.start, '%H:%M:%S').time())
        # self.to_dt = datetime.combine(today, datetime.strptime(self.end, '%H:%M:%S').time())
        # if self.to_dt < self.from_dt:
        #     self.to_dt = self.to_dt + timedelta(days=1)

        self.terminate = False

        super().__init__()


    def init_logs(self, unit_test = False):

        
        if unit_test:
            logger.setLevel(logging.DEBUG)            
        else:
            logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        log_file = os.path.join("../../logs/trading", f"{self.instrument}_{datetime.now(tz=timezone.utc).strftime('%m-%d')}_app.log")
        log_handler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)


    def start_trading(self, stop_after = None):

        logger.info("\n" + 100 * "-")
        logger.info ("Started New Trading Session")
        self.terminate = False

        logger.info (f"Getting  candles for: {self.instrument}")
        self.strategy.data = self.api.get_price_candles(pair_name=self.instrument, days=self.days)


        treads = []
        treads.append(threading.Thread(target=self.check_positions, args=(1 * 60,)))
        # treads.append(threading.Thread(target=self.check_trading_time, args=(1 * 60,)))
        treads.append(threading.Thread(target=self.refresh_strategy, args=(10,)))
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
                self.api.stream_prices(instrument=self.instrument, stop = stop_after, callback=self.new_price_ticker)
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
        self.api.stop_streaming()


    def check_trading_time(self, refresh = 60):
        pass
        # while not self.terminate:

        #     now = datetime.now(tz=timezone.utc)
        #     logger.debug(f"Check Trading Time: {now}, from: {self.from_dt}, to: {self.to_dt}")
            
        #     day = now.weekday()
        #     hour = now.hour
        #     if day == 4 and hour >= 19 and not self.strategy.stop_trading:
        #         logger.info("Friday after Trading Time - Terminating Trading")
        #         self.strategy.stop_trading = True
            

            # if self.from_dt - timedelta(minutes=90) <= now <= self.to_dt:
            #    self.strategy.stop_trading = True
            # elif not self.from_dt <= now <= self.to_dt:
            #     logger.info(f"Now: {now}, Trading Time: {self.from_dt} - {self.to_dt}")
            #     logger.info("Not Trading Time - Terminating Trading")
            #     self.terminate = True
            #     self.stop_streaming()
            #     break

            # time.sleep(refresh)


    def refresh_strategy(self, refresh = 30):

        i: int = 0

        while not self.terminate:

            logger.debug("Refreshing Strategy")

            try:

                temp_tick_data = self.tick_data.copy()
                self.tick_data.clear()

                if len(temp_tick_data) > 0:
                    df = pd.DataFrame(temp_tick_data, columns=["time", self.instrument, "bid", "bid_liquidity", "ask", "ask_liquidity", "status"])
                    df.set_index('time', inplace=True)    
                    df = df.resample("30s").last()
                    # logger.debug(f"Adding tickers length: {len(df)} | data: {df}")
                    self.strategy.add_tickers(ticker_df=df)

                self.strategy.calc_indicators()                
                self.strategy.set_strategy_indicators(row = None)
            
                try:
                    self.strategy.execute_strategy()
                except PauseTradingException as e:
                    logger.info(f"Caught Stop Loss Error. Continue Traiding...")
                    self.stop_loss_count = self.stop_loss_count + 1
                    # time.sleep(2 * 60 * 60)
                    
                    if self.stop_loss_count > 2:
                        logger.error(f"Stop Loss Count > 2. Terminating Trading")
                        self.terminate = True

            except Exception as e:
                logger.error("Exception occurred in refresh_strategy")
                logger.exception(e)
                i = i + 1
                if i > 20:
                    self.terminate = True
                    break

            time.sleep(refresh)


    def check_positions(self, refresh = 300): 

        i: int = 0
        print_logs: int = 0

        while not self.terminate:
            try:

                logger.debug("Check Positions")

                units = self.api.get_position(instrument = self.instrument)
                if not units == self.strategy.trading_session.have_units:
                    self.strategy.trading_session.have_units = units

                if print_logs % 5 == 0:
                    logger.info(f"Instrument: {self.instrument}, Units: {units}")

                print_logs = print_logs + 1
                time.sleep(refresh)

            except Exception as e:
                logger.error("Exception occurred in check_positions")
                logger.exception(e)
                i = i + 1
                if i > 20:
                    self.terminate = True
                    break
                time.sleep(5)
        
 
    def new_price_ticker(self, **kwargs):

        instrument = kwargs.get('instrument')
        date_time = kwargs.get('time')
        ask = kwargs.get('ask')
        ask_liquidity = kwargs.get('ask_liquidity')
        bid = kwargs.get('bid')
        bid_liquidity = kwargs.get('bid_liquidity')
        status = kwargs.get('status')

        if not (instrument is not None \
                and time is not None and bid is not None \
                    and ask is not None and status is not None):
            
                        logger.error(f"Invalid instrument price values!!!")
                        logger.error(f"Instrument: {instrument} | Time: {date_time} | Bid: {bid} | Bid Liquidity: {bid_liquidity} | Ask: {ask} | Ask Liquidity: {ask_liquidity} | Status: {status}")
                        return
        
        logger.debug(f"Instrument: {instrument} | Time: {date_time} | Bid: {bid} | Bid Liquidity: {bid_liquidity} | Ask: {ask} | Ask Liquidity: {ask_liquidity} | Status: {status}")

         # 2023-12-19T13:28:35.194571445Z
        pd_timestamp: pd.Timestamp = pd.to_datetime(date_time).replace(tzinfo=None)
        
        recent_tick = [pd_timestamp, (ask + bid)/2, bid, bid_liquidity, ask, ask_liquidity, status]
        self.tick_data.append(recent_tick)

        minute: int = pd_timestamp.minute
        second: int = pd_timestamp.second

        if minute in [0, 15, 30, 45] and second == 0:
            logger.info(f"Heartbeat: instrument: {self.instrument} | ask: {ask} | aks_liquidity: {ask_liquidity} | bid: {bid} | bid_liquidity: {bid_liquidity} | status: {status}")
 
  
        
    def terminate_session(self, cause):
        # self.stop_stream = True
        logger.info (cause)

        self.strategy.terminate()


    
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
