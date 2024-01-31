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

from trading.MyTT import RSI, SLOPE
from trading.trader import Trader
from trading.trader_strategy_bb_target_sma import BB_to_SMA_Strategy

from backtesting_strategy import Backtesting_Strategy

logger = logging.getLogger()

class BB_to_SMA_Back_Test():
    
    def __init__(self, conf_file, pairs_file, instrument, new = False):
        
        if new:
            logger.info("Running Backtesting_Strategy")
            self.strategy = Backtesting_Strategy(instrument, pairs_file)
        else:
            logger.info("Compare with BB_to_SMA_Strategy")
            self.strategy = BB_to_SMA_Strategy(instrument, pairs_file)

        self.api = tpqoa.tpqoa(conf_file)
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        self.start = config.get(instrument, 'start')
        self.end = config.get(instrument, 'end')
        logger.setLevel(logging.INFO)

        log_file = os.path.join("logs", "backtester_" + instrument + ("_new" if new else "_old") +".log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

    
    def get_history_with_all_prices(self):
        
        ask_prices: pd.DataFrame = self.get_history(price = "A")
        ask_prices.rename(columns = {"c":"ask"}, inplace = True)

        bid_prices: pd.DataFrame = self.get_history(price = "B")
        bid_prices.rename(columns = {"c":"bid"}, inplace = True)

        df: pd.DataFrame = pd.concat([ask_prices, bid_prices], axis=1)

        df [self.strategy.instrument] = df[['ask', 'bid']].mean(axis=1)

        return df

    def get_history(self, price = "M"):
        
        delta = 2
        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = delta)
        instrument = self.strategy.instrument
        
        df: pd.DataFrame = pd.DataFrame()
        for i in range(1, 2):           

            df_t = self.api.get_history(instrument = instrument, start = past, end = now,
                                granularity = "S30", price = price, localize = True).c.dropna().to_frame()
            df = pd.concat([df, df_t])
            now = past
            past = now - timedelta(days = delta)
            
            
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')
        df.sort_values(by='time', ascending=True, inplace=True)

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
        df["rsi_max"] = df ['RSI'].rolling(10).max()
        df["rsi_min"] = df ['RSI'].rolling(10).min()
        # df["rsi_mean"] = df ['RSI'].rolling(10).mean()
        # df["RSI_EMA"] = df.RSI.ewm(span=10, adjust=False, ignore_na = True).mean()
        # df["rsi_ema_max"] = df ['RSI_EMA'].rolling(10).max()
        # df["rsi_ema_min"] = df ['RSI_EMA'].rolling(10).min()


        # df["ema"] = df[instrument].ewm(span=10, adjust=False, ignore_na = True).mean()


        # df["slope"] = df[instrument].rolling(5).apply(lambda x: SLOPE(x.dropna().values, N=5))
        # df["slope_prev"] = df["slope"].shift(1)
        
        df["price_max"] = df [instrument].rolling(10).max()
        df["price_min"] = df [instrument].rolling(10).min()
        # df["price_mean"] = df [instrument].rolling(60).mean()


        df.dropna(subset=["RSI", "SMA"], inplace = True)

        # logger.info(df)

        return df
    
    def set_strategy_parameters(self, row):

            self.strategy.sma = row ['SMA']
            self.strategy.bb_lower = row ['Lower']
            self.strategy.bb_upper =  row ['Upper']
            
       
            self.strategy.rsi = row ['RSI']
            self.strategy.rsi_max = row ['rsi_max']
            self.strategy.rsi_min = row ['rsi_min']
            # self.strategy.rsi_mean = row ['rsi_mean']
            
            self.strategy.price_max = row ['price_max']
            self.strategy.price_min = row ['price_min']
            # self.strategy.price_mean = row ['price_mean']
            # self.strategy.slope = row ['slope']
            # self.strategy.slope_prev = row ['slope_prev']
       
            # self.strategy.rsi_ema = row ['RSI_EMA']
            # self.strategy.rsi_ema_max = row ['rsi_ema_max']
            # self.strategy.rsi_ema_min = row ['rsi_ema_min']
    
    def get_data(self, refresh = False):

        if refresh:                
            df = self.get_history_with_all_prices()
            df.to_pickle(f"../../data/backtest_{self.strategy.instrument}.pcl")
            # df.to_excel(f"../../data/backtest_{self.strategy.instrument}.xlsx")
        else:
            df = pd.read_pickle(f"../../data/backtest_{self.strategy.instrument}.pcl")

        df = self.calculate_indicators(df)
        df.to_excel(f"../../data/backtest_{self.strategy.instrument}.xlsx")
        # df.to_excel(f"../../data/backtest_{self.strategy.instrument}_with_indicators.xlsx")

        df = df.between_time(self.start, self.end)
        return df

    def start_trading_backtest(self, refresh = False):

        try:

            df:pd.DataFrame = self.get_data(refresh)

            self.have_units = 0

            for index, row in df.iterrows():
                self.set_strategy_parameters(row)
                ask = row ["ask"]
                bid = row ["bid"]
                trade_action = self.strategy.determine_action(bid, ask, self.have_units, self.units_to_trade)
                
                # logger.info(f"Time: {index}, bid: {bid}, ask: {ask}, action: {trade_action}")

                if trade_action != None:
                    self.have_units = self.strategy.trading_session.add_trade(trade_action, self.have_units, index)
            
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
 
    
    trader = BB_to_SMA_Back_Test(
        conf_file=config_file,
        pairs_file="../trading/pairs.ini",
        instrument=args.pair,
        new=(args.strategy  in ['New', 'new'])
    )
    trader.start_trading_backtest(refresh=(args.refresh in ['True', 'true']))


# python trader_strategy_bb_target_sma_backtest.py EUR_USD --refresh True --strategy New
