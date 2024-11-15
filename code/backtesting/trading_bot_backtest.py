import argparse
import configparser
import logging
import logging.handlers as handlers
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.api.oanda_api import OandaApi
from trading.strategies.base.strategy_exec import TradingStrategyExec
from trading.utils import utils

logger = logging.getLogger()

class TradingBacktester():
    
    def __init__(self, conf_file, pairs_file, instrument, days = 33, refresh = False):
        
        self.days = days
        self.refresh = refresh
        self.api = OandaApi(conf_file)
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))

        logger.setLevel(logging.INFO)
        
        log_file = os.path.join("logs", f"{instrument}_{days}.log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        # formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', utils.date_format)

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
        logger.info(f"Strategy Configuration \n + {config.items(instrument)}")

        self.strategy: TradingStrategyExec  = class_(instrument=instrument, pair_file=pairs_file, api = self.api, unit_test = False)
        self.strategy.backtest = True
    
    def get_history_with_all_prices(self):
        
        df: pd.DataFrame = self.api.get_price_candles(self.strategy.instrument, self.days)
               
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

            try:
                file_path = f"../../data/backtest_{self.strategy.instrument}_{self.days}.xlsx"
                if not os.path.exists(file_path):
                   logger.info("Saving indicators to Excel...")
                   self.strategy.data.to_excel(file_path)
                else:
                    logger.info(f"File: {file_path} already exists")
            except Exception as e:
                logger.error("Couldn't wtite to " + f"../../data/backtest_{self.strategy.instrument}_{self.days}.xlsx." + " File is open")
 
 
            pause_trading = None

            logger.info(f"Starting trading for {self.strategy.instrument}...")
            for index, row in self.strategy.data.iterrows():

                self.strategy.set_strategy_indicators(row=row, time=index)
                
                if pause_trading == None or index > pause_trading:
                    trade_action = self.strategy.determine_trade_action(trading_time=index)
                                        
                    if trade_action != None and trade_action.sl_trade:
                        logger.debug(f"Pausing trading for 5 minutes at {index}")
                        pause_trading = index + timedelta(minutes = 10)                        
        
            logger.info("Finished trading, printing report...")
            self.strategy.trading_session.print_trades()

            # logger.info("Saving trading report to Excel...")
            # date_stamp = datetime.now().strftime("%d_%H_%M")
            # self.strategy.trading_session.to_excel(f"../../data/backtest_results_{self.strategy.instrument}_{self.days}_{date_stamp}.xlsx")

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
