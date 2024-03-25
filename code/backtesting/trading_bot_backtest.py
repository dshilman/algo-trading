import argparse
import configparser
import logging
import logging.handlers as handlers
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.api.oanda_api import OandaApi
from trading.utils.errors import PauseTradingException
from trading.utils.tech_indicators import calculate_rsi, calculate_momentum
from trading.strategies.base.strategy_exec import TradingStrategyExec

logger = logging.getLogger()

class TradingBacktester():
    
    def __init__(self, conf_file, pairs_file, instrument, days = 33, refresh = False):
        
        self.days = days
        self.refresh = refresh
        self.api = OandaApi(conf_file)
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        self.start = config.get(instrument, 'start')
        self.end = config.get(instrument, 'end')

        logger.setLevel(logging.INFO)

        log_file = os.path.join("logs", f"{instrument}_{days}.log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

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
        self.strategy: TradingStrategyExec  = class_(instrument=instrument, pair_file=pairs_file, api = self.api, unit_test = False)
        
    
    def get_history_with_all_prices(self):
        
        df: pd.DataFrame = self.api.get_price_candles(self.strategy.instrument, self.days)
               
        # df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

        return df

    def get_data(self):

        pcl_file_name = f"../../data/backtest_{self.strategy.instrument}_{self.days}.pcl"
        if self.refresh:
            logger.info("Getting data from OANDA API...")                
            df = self.get_history_with_all_prices()
            logger.info(f"Saving data to {pcl_file_name}")
            df.to_pickle(pcl_file_name)
            # df.to_excel(f"../../data/backtest_{self.strategy.instrument}.xlsx")
        else:
            logger.info(f"Reading data from {pcl_file_name}")
            df = pd.read_pickle(pcl_file_name)
      
        # df = df.between_time(self.start, self.end)
        return df

    def start_trading_backtest(self):

        try:

            self.strategy.data = self.get_data()

            logger.info("Calculating indicators...")
            self.strategy.calc_indicators()
            # self.strategy.data.to_excel(f"../../data/backtest_{self.strategy.instrument}.xlsx")
    
            logger.info(f"Starting trading for {self.strategy.instrument}...")

            pause_trading = None

            for index, row in self.strategy.data.iterrows():

                self.strategy.set_strategy_indicators(row=row, print_ind=False)
                
                if pause_trading == None or index > pause_trading:
                    trade_action = None
                    try:
                        trade_action = self.strategy.determine_trade_action(trading_time=index)
                    except PauseTradingException as e:
                        logger.info(f"Pausing trading for {e.hours} hour(s) at {index}")
                        pause_trading = index + timedelta(hours = e.hours)
                        continue
                                        
                    if trade_action != None:
                        # self.strategy.print_indicators()
                        self.strategy.trading_session.add_trade(trade_action=trade_action, date_time=index, rsi=self.strategy.rsi)
                        if trade_action.sl_trade:
                            logger.info(f"Pausing trading for 5 minutes at {index}")
                            pause_trading = index + timedelta(minutes = 5)                        
            
            logger.info("Finished trading, printing report...")
            self.strategy.trading_session.print_trades()

        except Exception as e:
            logger.exception("Exception occurred")
        finally:
            logger.info("Stoping Backtesting")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('pair', type=str, help='pair')

    parser.add_argument('--days', type = int, default=33, help='Number of days, numeric only')
    parser.add_argument('--refresh', choices=['True', 'False', 'true', 'false'], default="False", type = str, help='Refresh data')
    args = parser.parse_args()

    
    config_file = os.path.abspath(path="../../config/oanda.cfg")
    print (f"oanda config file: {config_file}")
    if os.path.exists(config_file) == False:
        logger.error(f"Config file does not exist: {config_file}")
        exit(1) 
 
    
    trader = TradingBacktester(
        conf_file=config_file,
        pairs_file="../trading/pairs.ini",
        instrument=args.pair, days=args.days, refresh=(args.refresh in ['True', 'true']))

    trader.start_trading_backtest()


# python trading_bot_backtest.py EUR_USD --refresh True
