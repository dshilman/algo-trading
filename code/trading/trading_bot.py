from collections import deque
import argparse
import configparser
import logging
import logging.handlers as handlers
import os
import sys
import threading
from requests.exceptions import ChunkedEncodingError
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

# Constants
MAX_DEQUE_SIZE = utils.ticker_data_size * 900  # 30-second ticks for 5-min candles
MAX_ITERATIONS = sys.maxsize  # Replaced invalid integer literal
THREAD_START_DELAY = 5  # seconds
MAX_ERROR_COUNT = 20

class Trader():
    def __init__(self, conf_file, pair_file, trading_strategy, unit_test = False):

        self.init_logs(name=trading_strategy, unit_test=unit_test)

        self.api = OandaApi(conf_file)
        self.streaming = False


        config = configparser.ConfigParser()  
        config.read(pair_file)

        self.ticker_data_deque = deque(maxlen=MAX_DEQUE_SIZE)
        self.ticker_data_lock = threading.Lock()  # Thread safety for deque access
        
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


    def start_trading(self, stop_after = sys.maxsize):
        """Start trading session with streaming and strategy execution threads."""
        logger.info("\n" + 100 * "-")
        logger.info("Started New Trading Session")
        self.terminate = False

        # Reconcile positions on startup
        self.reconcile_positions()
        
        threads = []
        threads.append(threading.Thread(target=self.start_streaming, args=(), daemon=True))
        threads.append(threading.Thread(target=self.refresh_strategy, args=(stop_after,), daemon=True))

        for t in threads:
            t.start()
            sleep(THREAD_START_DELAY)
        
        for t in threads:
            t.join()

        self.terminate_session("Finished Trading Session")

    
    def reset_dequeue(self, candles: pd.DataFrame):
        """Reset deque with historical candle data. Thread-safe."""
        with self.ticker_data_lock:
            self.ticker_data_deque.clear()
            for index, row in candles.iterrows():
                self.ticker_data_deque.append((index, row["close"], row["bid"], row["ask"]))    


    def start_streaming(self):
        """Start streaming price data from API. Handles reconnection on errors."""
        candles = self.api.get_latest_price_candles(
            pair_name=self.strategy.instrument, 
            granularity=utils.granularity, 
            count=utils.count
        )
        self.reset_dequeue(candles)
        
        self.streaming = True
        error_count: int = 0

        while not self.terminate:

            try:
                logger.info("Start streaming prices for %s", self.strategy.instrument)
                self.api.stream_prices(instrument=self.strategy.instrument, callback=self.new_price_ticker)
                logger.info("Stopped streaming prices")
                self.terminate = True
                break

            except ChunkedEncodingError as e:
                logger.warning("ChunkedEncodingError - reconnecting: %s", e)
                sleep(2)  # Brief delay before reconnect
                
            except Exception as e:
                logger.error("Error in start_streaming: %s", e)
                logger.exception(e)
                error_count += 1
                
                if error_count > MAX_ERROR_COUNT:
                    logger.error("Too many errors (%d). Stopped streaming prices", error_count)
                    self.terminate = True
                    break
                    
                sleep(5)  # Longer delay on non-network errors


    def stop_streaming(self):
        """Stop streaming prices gracefully."""
        logger.info("Stop Stream")
        self.api.stop_streaming()
        
    def reconcile_positions(self):
        """Reconcile bot's position tracking with actual broker positions on startup."""
        try:
            position = self.api.get_position(self.strategy.instrument)
            if position:
                actual_units = int(position.get('long', {}).get('units', 0)) + int(position.get('short', {}).get('units', 0))
                if actual_units != 0:
                    logger.warning("Position mismatch detected. Actual: %d, Expected: 0", actual_units)
                    self.strategy.trading_session.have_units = actual_units
                    logger.info("Position reconciled: %d units", actual_units)
                else:
                    logger.info("Position reconciliation: No open positions")
        except Exception as e:
            logger.error("Failed to reconcile positions: %s", e)
            logger.exception(e)



    def refresh_strategy(self, stop_after=MAX_ITERATIONS):
        """Execute trading strategy periodically. Thread-safe."""
        error_counter: int = 0
        exec_counter: int = 0

        while exec_counter < stop_after and not self.terminate:
            
            logger.debug("Inside refresh strategy loop")

            try:

                trading_time = datetime.now(tz=timezone.utc)
                logger.debug (f"Refresh Strategy... {trading_time.strftime('%H:%M:%S')}")

                exec_counter = exec_counter + 1                        
                # logger.info("")
                # logger.info(f"Start executing strategy... {exec_counter}")

                if not self.streaming:
                    # logger.info(f"Get candles for {self.strategy.instrument}")
                    candles = self.api.get_latest_price_candles(pair_name=self.strategy.instrument, granularity=utils.granularity, count=utils.count)
                    self.reset_dequeue(candles)

                # Thread-safe copy of ticker data
                with self.ticker_data_lock:
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

    def exec_strategy(self, ticker_data_df: pd.DataFrame, trading_time: datetime) -> Trade_Action:

        # logger.debug(f"Ticker data: {ticker_data_df}")

        if len(ticker_data_df.index) < utils.ticker_data_size:
            logger.info(f"Skip strategy execution, {len(ticker_data_df.index)} ticker data size is too small. From: {ticker_data_df.index [0] if len(ticker_data_df.index) > 0 else 'N/A'}, to: {ticker_data_df.index [-1] if len(ticker_data_df.index) > 0 else 'N/A'}")
            return # type: ignore

        last_candle_time: pd.Timestamp = ticker_data_df.index[-1]
        if trading_time - last_candle_time > timedelta(seconds=30):
            logger.info(f"Ticker data is too stale: {last_candle_time.strftime('%H:%M:%S')}, trading time: {trading_time.strftime('%H:%M:%S')}. Try again soon.")
            return # type: ignore


        self.strategy.data = ticker_data_df
        self.strategy.calc_indicators()                
        self.strategy.set_strategy_indicators(ticker_data_df.iloc[-1])

        self.strategy.trading_session.have_units = int(self.api.get_position(instrument = self.strategy.instrument))
        trade_action = self.strategy.execute_strategy(trading_time)

        return trade_action

 
    def new_price_ticker(self, **kwargs):
        """Callback for new price ticks from streaming API. Thread-safe."""
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
        
        with self.ticker_data_lock:
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
