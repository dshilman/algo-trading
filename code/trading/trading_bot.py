from collections import deque
import argparse
import configparser
import logging
import logging.handlers as handlers
import os
import sys
import threading
from time import sleep
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Any
import pandas as pd
from pytz import utc


file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.dom.trade import Trade_Action
from trading.api.oanda_api import OandaApi, StopTradingEvent
from trading.strategies.base.strategy_exec import TradingStrategyExec
from trading.utils import utils


logger = logging.getLogger()

class Trader():
    def __init__(self, conf_file, pair_file, trading_strategy, unit_test = False):

        self.init_logs(name=trading_strategy, unit_test=unit_test)

        self.api = OandaApi(conf_file)
        self.streaming = False


        config = configparser.ConfigParser()  
        config.read(pair_file)

        # self.days = int(config.get(self.strategy.instrument, 'days'))
        # self.start = config.get(self.strategy.instrument, 'start')
        # self.end = config.get(self.strategy.instrument, 'end')

        self.ticker_data_deque = deque(maxlen=utils.ticker_data_size * 900)
        
        class_ = None
        strategy = config.get(trading_strategy, 'strategy')

        try:
            modules = strategy.split(sep=".", maxsplit=2)
            logger.info(f"Loading:{modules[0]} strategy")
            module = __import__(f"trading.strategies.{modules[0]}", fromlist=[f"{modules[1]}"])
            logger.info(f"Loading:{modules[1]} class")
            class_ = getattr(module, modules[1])
        except Exception as e:            
            logger.error(f"Strategy not found for {trading_strategy}", e)
            raise Exception(f"Strategy not found for {trading_strategy}")

        logger.info(f"Running:{class_} strategy")
        self.strategy: TradingStrategyExec  = class_(trading_strategy=trading_strategy, pair_file=pair_file, api = self.api, unit_test = unit_test)
        logger.info(f"Strategy Configuration \n + {config.items(trading_strategy)}")

        self.terminate = False

        super().__init__()


    def init_logs(self, name, unit_test = False):

        
        if unit_test:
            logger.setLevel(logging.DEBUG)            
        else:
            logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', utils.date_format)

        log_dir = os.path.join(os.path.dirname(__file__), "../../logs/trading")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"{name}_{datetime.now(tz=timezone.utc).strftime('%m-%d')}_app.log")
        log_handler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)


    def start_trading(self, stop_after = 999999999999999999999999999999999999999999999999999999):

        logger.info("\n" + 100 * "-")
        logger.info ("Started New Trading Session")
        self.terminate = False

        threads = []
        # threads.append(threading.Thread(target=self.check_positions, args=(1 * 60,)))
        threads.append(threading.Thread(target=self.start_streaming, args=()))
        threads.append(threading.Thread(target=self.refresh_strategy, args=(stop_after,)))

        # self.refresh_strategy(refresh=5, stop_after=999999999999999999999999999999999999999999)

        for t in threads:
            t.start()
            sleep(5)
        
        for t in threads:
            t.join()

        self.terminate_session("Finished Trading Session")

    
    def reset_dequeue(self, candles: pd.DataFrame):

        self.ticker_data_deque.clear()
        for index, row in candles.iterrows():
            self.ticker_data_deque.append((index, row["close"], row["bid"], row["ask"]))    


    def start_streaming(self):

        candles = self.api.get_latest_price_candles(pair_name=self.strategy.instrument, granularity=utils.granularity, count=utils.count)
        self.reset_dequeue(candles)
        
        self.streaming = True
        error_count: int = 0

        while not self.terminate:

            try:
                logger.info ("Start streaming prices")
                self.api.stream_prices(instrument=self.strategy.instrument, callback=self.new_price_ticker)
                logger.info("Stopped streaming prices")
                self.terminate = True
                break

            except Exception as e:
                logger.error(f"Error in start_streaming")
                logger.exception(e)
                error_count = error_count + 1
                if error_count > 20:
                    logger.info("Too many errors. Stopped streaming prices")
                    self.terminate = True
                    break


    def stop_streaming(self):

        logger.info ("Stop Stream")
        self.api.stop_streaming()



    def refresh_strategy(self, stop_after=99999999999999999999999999):

        error_counter: int = 0
        exec_counter: int = 0

        while exec_counter < stop_after and not self.terminate:
            
            logger.debug("Inside refresh strategy loop")

            try:

                trading_time = datetime.now(tz=timezone.utc)
                logger.debug (f"Refresh Strategy... {trading_time}")

                exec_counter = exec_counter + 1                        
                # logger.info("")
                # logger.info(f"Start executing strategy... {exec_counter}")

                if not self.streaming:
                    # logger.info(f"Get candles for {self.strategy.instrument}")
                    candles = self.api.get_latest_price_candles(pair_name=self.strategy.instrument, granularity=utils.granularity, count=utils.count)
                    self.reset_dequeue(candles)

                ticker_data_list = list(self.ticker_data_deque)                        
                ticker_data_df = self.strategy.to_5_min_candles(ticker_data_list, trading_time)

                # logger.info("Excute strategy")
                self.exec_strategy(ticker_data_df, trading_time)
           
                if exec_counter % 100 == 0:
                    logger.info("\n" + self.strategy.data[-10:].to_string(header=True))
                    logger.info("")

                sleep(30)
 
            except Exception as e:
                logger.error("Exception occurred in refresh_strategy")
                logger.exception(e)
                error_counter = error_counter + 1                
                if error_counter > 20:
                    logger.error(f"Too many errors: {error_counter}")
                    break
   
        self.terminate = True

    def exec_strategy(self, ticker_data_df: pd.DataFrame, trading_time) -> Trade_Action:

        # logger.debug(f"Ticker data: {ticker_data_df}")

        if len(ticker_data_df.index) < utils.ticker_data_size:
            logger.info(f"Skip strategy execution, {len(ticker_data_df.index)} ticker data size is too small. From: {ticker_data_df.index [0] if len(ticker_data_df.index) > 0 else 'N/A'}, to: {ticker_data_df.index [-1] if len(ticker_data_df.index) > 0 else 'N/A'}")
            return # type: ignore

        last_candle_time: pd.Timestamp = ticker_data_df.index[-1]
        if trading_time - last_candle_time > timedelta(seconds=30):
            logger.info(f"Ticker data is too stale: {last_candle_time}, trading time: {trading_time}. Try again soon.")
            return # type: ignore


        self.strategy.data = ticker_data_df
        self.strategy.calc_indicators()                
        self.strategy.set_strategy_indicators(ticker_data_df.iloc[-1])

        self.strategy.trading_session.have_units = int(self.api.get_position(instrument = self.strategy.instrument))
        trade_action = self.strategy.execute_strategy(trading_time)

        return trade_action


    def check_positions(self, refresh = 300): 

        i: int = 0
        print_logs: int = 0

        while not self.terminate:
            try:

                logger.debug("Check Positions")

                units = self.api.get_position(instrument = self.strategy.instrument)
                if not units == self.strategy.trading_session.have_units:
                    self.strategy.trading_session.have_units = int(units)

                if print_logs % 5 == 0:
                    logger.info(f"Instrument: {self.strategy.instrument}, Units: {units}")

                print_logs = print_logs + 1
                sleep(refresh)

            except Exception as e:
                logger.error("Exception occurred in check_positions")
                logger.exception(e)
                i = i + 1
                if i > 20:
                    self.terminate = True
                    break
                sleep(5)
        
 
    def new_price_ticker(self, **kwargs):

        if self.terminate:
            raise StopTradingEvent("Stop Trading")
        
        instrument = kwargs.get('instrument')
        date_time = kwargs.get('time')
        ask = kwargs.get('ask')
        bid = kwargs.get('bid')
        
        # logger.debug(f"Instrument: {instrument} | Time: {date_time} | Bid: {bid} | Ask: {ask}")

         # 2023-12-19T13:28:35.194571445Z
        if date_time is None:
            logger.error("date_time is None, cannot convert to pd.Timestamp")
            return

        pd_timestamp: pd.Timestamp = pd.to_datetime(date_time, utc=True)
        
        recent_tick = (pd_timestamp, (ask + bid)/2, bid, ask) # type: ignore
        self.ticker_data_deque.append(recent_tick)
        
        
    def terminate_session(self, cause):
        # self.stop_stream = True
        logger.info (cause)

        self.strategy.trading_session.print_trades()


    
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('trading_strategy', type=str, help='trading_strategy')
    args = parser.parse_args()

    config_file = os.path.abspath(path="config/oanda.cfg")
    # print (f"oanda config file: {config_file}")
    if os.path.exists(config_file) == False:
        print(f"Config file does not exist: {config_file}")
        exit(1) 
    
    trader = Trader(
        conf_file=config_file,
        pair_file="code/trading/pairs.ini",
        trading_strategy=args.trading_strategy,
        unit_test=False
    )
    trader.start_trading()
    
# python trading_bot.py EUR_USD#1
