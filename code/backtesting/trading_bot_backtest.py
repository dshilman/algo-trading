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
    
    def __init__(self, conf_file, pairs_file, trading_strategy, days = 33, refresh = False):
        
        self.days = days
        self.refresh = refresh
        self.api = OandaApi(conf_file)
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.units_to_trade = int(config.get(trading_strategy, 'units_to_trade'))

        logger.setLevel(logging.INFO)
        
        log_file = os.path.join("logs", f"{trading_strategy}_{days}.log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        # formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', utils.date_format)

        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

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
        logger.info(f"Strategy Configuration \n + {config.items(trading_strategy)}")

        self.strategy: TradingStrategyExec  = class_(trading_strategy=trading_strategy, pair_file=pairs_file, api = self.api, unit_test = False)
        self.strategy.backtest = True
    
    def get_history_with_all_prices(self):
        
        df: pd.DataFrame = self.api.get_price_candles(self.strategy.instrument, self.days)
               
        return df

    def get_data(self):

        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        pcl_file_name = os.path.join(data_dir, f"backtest_{self.strategy.instrument}_{self.days}.pcl")
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

            excel_file_name = None

            try:

                data_dir = os.path.join(os.path.dirname(__file__), "data")
                os.makedirs(data_dir, exist_ok=True)
                excel_file_name = os.path.join(data_dir, f"backtest_{self.strategy.instrument}_{self.days}.xlsx")

                if not os.path.exists(excel_file_name):
                   logger.info("Saving indicators to Excel...")
                   df = self.strategy.data.copy()
                   df.index =  pd.to_datetime(df.index).tz_convert(None)           
                   df.to_excel(excel_file_name)
                else:
                    logger.info(f"File: {excel_file_name} already exists")
            except Exception as e:
                logger.error(f"Couldn't wtite to {excel_file_name}", e)
 
 
            pause_trading = None

            logger.info(f"Starting trading for {self.strategy.instrument}...")
            for index, row in self.strategy.data.iterrows():

                self.strategy.set_strategy_indicators(row=row)
                
                if pause_trading == None or index > pause_trading:
                    trade_action = self.strategy.determine_trade_action(trading_time=index)
                    # if trade_action is not None and trade_action.sl_trade:
                    #     pause_trading = index + timedelta(minutes=5) # type: ignore
        
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
    parser.add_argument('trading_strategy', type=str, help='trading_strategy')

    parser.add_argument('--days', type = int, default=3, help='Number of days, numeric only')
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
        trading_strategy=args.trading_strategy, days=args.days, refresh=(args.refresh in ['True', 'true']))

    trader.start_trading_backtest()


# python trading_bot_backtest.py EUR_USD#2 --refresh True
