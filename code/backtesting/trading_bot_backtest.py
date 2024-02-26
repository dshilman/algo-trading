import argparse
import configparser
import logging
import logging.handlers as handlers
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytz
import tpqoa

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.api import OANDA_API
from trading.errors import PauseTradingException
from trading.MyTT import RSI, SLOPE, calculate_rsi
from trading.strategy import TradingStrategy

logger = logging.getLogger()

class TradingBacktester():
    
    def __init__(self, conf_file, pairs_file, instrument):
        
        self.api = OANDA_API(conf_file)
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        self.start = config.get(instrument, 'start')
        self.end = config.get(instrument, 'end')
        logger.setLevel(logging.INFO)

        log_file = os.path.join("logs", f"{instrument}.log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

        class_ = None

        try:
            module = __import__(f"trading.strategies.{instrument.lower()}_strategy", fromlist=[f"{instrument}_Strategy"])
            class_ = getattr(module, f"{instrument}_Strategy")
        except:
            logger.error(f"Strategy not found for {instrument}")
            class_ = TradingStrategy

        logger.info(f"Running:{class_} strategy")
        self.strategy: TradingStrategy  = class_(instrument=instrument, pair_file=pairs_file, api = self.api, unit_test = False)

        self.days = 100
        self.refresh = False
    
    def get_history_with_all_prices(self):
        
        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = self.days)
        instrument = self.strategy.instrument

        df: pd.DataFrame = self.api.get_history_with_all_prices_by_period(instrument, past, now)
               
        # df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

        return df

    def calculate_indicators(self, input_df: pd.DataFrame):

        instrument = self.strategy.instrument
        SMA = self.strategy.sma_value
        dev = self.strategy.dev

        df = input_df.copy()
        df["SMA"] = df[instrument].rolling(SMA).mean()

        df["price_slope"] = df[instrument].rolling(SMA).apply(lambda x: SLOPE(x.dropna().values))

        std = df[instrument].rolling(SMA).std() * dev
        
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std
        
        # df["std"] = df[instrument].rolling(SMA).std()
        # df["std_sma"] = df["std"].rolling(SMA).mean()
        
        rsi_periods = int(SMA/2)
        df["RSI"] = df[instrument].rolling(rsi_periods).apply(lambda x: calculate_rsi(x.values, rsi_periods))
        df["rsi_momentum"] = df.RSI.rolling(8).apply(lambda x: (x.iloc[0] - x.iloc[-1]) / x.iloc[0])
        df["rsi_momentum_prev"] = df ["rsi_momentum"].shift(1)
        df["rsi_prev"] = df["RSI"].shift(1)
        df["rsi_max"] = df ['RSI'].rolling(8).max()
        df["rsi_min"] = df ['RSI'].rolling(8).min()

        df["price_max"] = df [instrument].rolling(8).max()
        df["price_min"] = df [instrument].rolling(8).min()

        df["momentum"] = df[instrument].rolling(8).apply(lambda x: (x.iloc[0] - x.iloc[-1])/ x.iloc[0])        
        df["momentum_prev"] = df["momentum"].shift(1)
        df["momentum_max"] = df ['momentum'].rolling(8).max()
        df["momentum_min"] = df ['momentum'].rolling(8).min()
        df["momentum_avg"] = df ['momentum'].rolling(8).max()
        df["momentum_std"] = df ['momentum'].rolling(8).min()


        df.dropna(subset=["RSI", "SMA"], inplace = True)

        return df
    
    def set_strategy_parameters(self, row):

            self.strategy.sma = row ['SMA']

            self.strategy.price_slope = row ['price_slope']

            self.strategy.bb_lower = row ['Lower']
            self.strategy.bb_upper =  row ['Upper']
                   
            self.strategy.rsi = round(row ['RSI'], 4)
            self.strategy.rsi_prev = round(row ['rsi_prev'], 4)
            self.strategy.rsi_max = round(row ['rsi_max'], 4)
            self.strategy.rsi_min = round(row ['rsi_min'], 4)

            self.strategy.rsi_momentum = round(row ["rsi_momentum"], 6)
            self.strategy.rsi_momentum_prev = round(row ["rsi_momentum_prev"], 6)

            
            self.strategy.price = row [self.strategy.instrument]
            self.strategy.price_max = row ['price_max']
            self.strategy.price_min = row ['price_min']

            self.strategy.ask = row ["ask"]
            self.strategy.bid = row ["bid"]

            self.strategy.momentum = row ['momentum']
            self.strategy.momentum_prev = row ['momentum_prev']
            self.strategy.momentum_max= row ['momentum_max']
            self.strategy.momentum_min = row ['momentum_min']
            self.strategy.momentum_avg = row ['momentum_avg']
            self.strategy.momentum_std = row ['momentum_std']


    def get_data(self):

        pcl_file_name = f"../../data/backtest_{self.strategy.instrument}_t.pcl"
        if self.refresh:                
            df = self.get_history_with_all_prices()
            df.to_pickle(pcl_file_name)
            # df.to_excel(f"../../data/backtest_{self.strategy.instrument}.xlsx")
        else:
            df = pd.read_pickle(pcl_file_name)

        df = self.calculate_indicators(df)
        # df.to_excel(f"../../data/backtest_{self.strategy.instrument}.xlsx")
        # df.to_excel(f"../../data/backtest_{self.strategy.instrument}_with_indicators.xlsx")

        # df = df.between_time(self.start, self.end)
        return df

    def start_trading_backtest(self):

        try:

            df:pd.DataFrame = self.get_data()

            self.have_units = 0

            pause_trading = None

            for index, row in df.iterrows():

                self.set_strategy_parameters(row)
                
                if pause_trading == None or index > pause_trading:
                    trade_action = None
                    try:
                        trade_action = self.strategy.determine_trade_action(self.have_units, index)
                    except PauseTradingException as e:
                        logger.info(f"Pausing trading for {e.hours} hour(s) at {index}")
                        pause_trading = index + timedelta(hours = e.hours)
                        continue
                                        
                    if trade_action != None:
                        # self.strategy.print_indicators()
                        self.have_units = self.strategy.trading_session.add_trade(trade_action, self.have_units, index, self.strategy.rsi)
                        if trade_action.sl_trade:
                            logger.info(f"Pausing trading for 2 hours at {index}")
                            pause_trading = index + timedelta(hours = 2)                        
            
            self.strategy.trading_session.print_trades()

        except Exception as e:
            logger.exception("Exception occurred")
        finally:
            logger.info("Stoping Backtesting")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('pair', type=str, help='pair')

    parser.add_argument('--refresh', choices=['True', 'False', 'true', 'false'], default="False", type = str, help='Refresh data')
    parser.add_argument('--days', type = int, default=0, help='Number of days, numeric only')
    args = parser.parse_args()

    
    config_file = os.path.abspath(path="../../config/oanda.cfg")
    print (f"oanda config file: {config_file}")
    if os.path.exists(config_file) == False:
        logger.error(f"Config file does not exist: {config_file}")
        exit(1) 
 
    
    trader = TradingBacktester(
        conf_file=config_file,
        pairs_file="../trading/pairs.ini",
        instrument=args.pair)

    trader.days = args.days
    trader.refresh = (args.refresh in ['True', 'true'])
    trader.start_trading_backtest()


# python trading_bot_backtest.py EUR_USD --refresh True
