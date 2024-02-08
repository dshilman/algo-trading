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

from trading.MyTT import RSI
from trading.strategy import TradingStrategy
from trading.api import OANDA_API

from backtesting_strategy import Backtesting_Strategy

logger = logging.getLogger()

class TradingBacktester():
    
    def __init__(self, conf_file, pairs_file, instrument, new = False):
        
        self.api = OANDA_API(conf_file)
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        self.start = config.get(instrument, 'start')
        self.end = config.get(instrument, 'end')
        logger.setLevel(logging.INFO)

        log_file = os.path.join("logs", f"{instrument}_{('new' if new else 'old')}.log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

        if new:
            logger.info("Running new strategy")
            self.strategy = Backtesting_Strategy(instrument, pairs_file, logger)
        else:
            logger.info("Running existing strategy")
            self.strategy = TradingStrategy(instrument, pairs_file, logger)

    
    def get_history_with_all_prices(self, days = 100):
        
        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = days)
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
        std = df[instrument].rolling(SMA).std() * dev
        
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std
        
        df["RSI"] = df[instrument].rolling(29).apply(lambda x: RSI(x.values, N=28))
        df["rsi_max"] = df ['RSI'].rolling(8).max()
        df["rsi_min"] = df ['RSI'].rolling(8).min()

        df["price_max"] = df [instrument].rolling(8).max()
        df["price_min"] = df [instrument].rolling(8).min()
        df ["momentum"] = df[instrument].rolling(8).apply(lambda x: (x.iloc[0] - x.iloc[-1]) / x.iloc[0])


        df.dropna(subset=["RSI", "SMA"], inplace = True)

        return df
    
    def set_strategy_parameters(self, row, df):

            self.strategy.sma = row ['SMA']
            self.strategy.bb_lower = row ['Lower']
            self.strategy.bb_upper =  row ['Upper']
            
       
            self.strategy.rsi = row ['RSI']
            self.strategy.rsi_max = row ['rsi_max']
            self.strategy.rsi_min = row ['rsi_min']
            self.strategy.rsi_hist = df.RSI.iloc[-8:].values
            
            self.strategy.price_max = row ['price_max']
            self.strategy.price_min = row ['price_min']
            self.strategy.ask = row ["ask"]
            self.strategy.bid = row ["bid"]

            self.strategy.momentum = row ['momentum']
            self.strategy.momentum_prev = df.momentum.iloc[-2] if len(df) > 2 else 0


    def get_data(self, refresh = False):

        if refresh:                
            df = self.get_history_with_all_prices(150)
            df.to_pickle(f"../../data/backtest_{self.strategy.instrument}.pcl")
            # df.to_excel(f"../../data/backtest_{self.strategy.instrument}.xlsx")
        else:
            df = pd.read_pickle(f"../../data/backtest_{self.strategy.instrument}.pcl")

        df = self.calculate_indicators(df)
        # df.to_excel(f"../../data/backtest_{self.strategy.instrument}.xlsx")
        # df.to_excel(f"../../data/backtest_{self.strategy.instrument}_with_indicators.xlsx")

        df = df.between_time(self.start, self.end)
        return df

    def start_trading_backtest(self, refresh = False):

        try:

            df:pd.DataFrame = self.get_data(refresh)

            self.have_units = 0

            stop_loss_date = None
            i = 0

            for index, row in df.iterrows():
                self.set_strategy_parameters(row, df.iloc[: i])
                
                if stop_loss_date == None or index > stop_loss_date:
                    trade_action = self.strategy.determine_trade_action(self.have_units)
                    
                    if trade_action != None:
                        self.have_units = self.strategy.trading_session.add_trade(trade_action, self.have_units, index)
                        if trade_action.sl_trade:
                            stop_loss_date = index + timedelta(hours = 2)                        
                i += 1

            
            self.strategy.trading_session.print_trades()

        except Exception as e:
            logger.exception("Exception occurred")
        finally:
            logger.info("Stopping Backtesting")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('pair', type=str, help='pair')

    parser.add_argument('--refresh', choices=['True', 'False', 'true', 'false'], default="False", type = str, help='Refresh data')
    parser.add_argument('--strategy', choices=['Old', 'New', 'old', 'new'], default='old', help='Which strategy to use')
    args = parser.parse_args()

    
    config_file = os.path.abspath(os.environ.get("oanda_config", "../../config/oanda_demo.cfg"))
    print (f"oanda config file: {config_file}")
    if os.path.exists(config_file) == False:
        logger.error(f"Config file does not exist: {config_file}")
        exit(1) 
 
    
    trader = TradingBacktester(
        conf_file=config_file,
        pairs_file="../trading/pairs.ini",
        instrument=args.pair,
        new=(args.strategy  in ['New', 'new'])
    )
    trader.start_trading_backtest(refresh=(args.refresh in ['True', 'true']))


# python trading_bot_backtest.py EUR_USD --refresh True --strategy New