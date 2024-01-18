import configparser
import logging
import logging.handlers as handlers
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytz
import tpqoa

# sys.path.appendappend("code")
import sys
from pathlib import Path # if you haven't already done so
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.trader import Trader
# from trading.trader_strategy_sma_target_bb import SMA_to_BB_Strategy
from trading.MyTT import RSI


logger = logging.getLogger("back_tester_sma_2_bb")

class SMA_to_BB_Back_Test():
    
    def __init__(self, conf_file, pairs_file, instrument):
        
        # self.strategy = SMA_to_BB_Strategy(instrument, pairs_file)
        self.strategy = None
        self.api = tpqoa.tpqoa(conf_file)
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        self.start = config.get(instrument, 'start')
        self.end = config.get(instrument, 'end')
        logger.setLevel(logging.INFO)

        log_file = os.path.join("logs", "backtester_" + instrument + ".log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

    def calculate_indicators(self, df):

        instrument = self.strategy.instrument
        SMA = self.strategy.SMA
        dev = self.strategy.dev
        df["SMA"] = df[instrument].rolling(SMA).mean()
        
        target = df[instrument].rolling(SMA).std() * dev
        
        df["Lower"] = df["SMA"] - target
        df["Upper"] = df["SMA"] + target
        df["RSI"] = df [instrument].rolling(15).apply(lambda x: RSI(x.values, N=14))
           
        df.dropna(subset=['Lower', 'RSI'], inplace=True)
        df ['rsi_max'] = df ["RSI"].rolling(5).max()
        df ['rsi_min'] = df ["RSI"].rolling(5).min()
        df ["price_max"] = df [instrument].rolling(5).max()
        df ["price_min"] = df [instrument].rolling(5).min()

        return df
    
    def get_history(self):
        
        delta = 5
        now = datetime.utcnow()
        now = now - timedelta(microseconds = now.microsecond)
        past = now - timedelta(days = delta)
        
        df: pd.DataFrame = pd.DataFrame()
        for i in range(1, 20):           

            instrument = self.strategy.instrument

            df_t = self.api.get_history(instrument = instrument, start = past, end = now,
                                granularity = "M1", price = "M", localize = True).c.dropna().to_frame()
            df = pd.concat([df, df_t])
            now = past
            past = now - timedelta(days = delta)

        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')
        df.sort_values(by='time', ascending=True, inplace=True)
        df.rename(columns = {"c":instrument}, inplace = True)

        return df

    def set_strategy_parameters(self, row):
            
            self.strategy.rsi_max = row ['rsi_max']
            self.strategy.rsi_min = row ['rsi_min']
            self.strategy.bb_lower = row ['Lower']
            self.strategy.bb_upper =  row ['Upper']
            self.strategy.sma = row ['SMA']
            self.strategy.rsi = row ['RSI']
            self.strategy.price_max = row ['price_max']
            self.strategy.price_min = row ['price_min']

    def start_trading_backtest(self, refresh = False):

        try:

            if refresh:
                
                df:pd.DataFrame = self.get_history()
                df = self.calculate_indicators(df)
                df.to_pickle(f"../../data/backtest_{self.strategy.instrument}.pcl")
            else:
                df = pd.read_pickle(f"../../data/backtest_{self.strategy.instrument}.pcl")


            df = df.between_time(self.start, self.end)

            self.have_units = 0
            self.pl:float = 0

            self.go_short = 0
            self.go_long = 0
            self.close_short = 0
            self.close_long = 0
            self.outstanding = 0

            self.trades = []

            self.i:int = 0

            for index, row in df.iterrows():

                self.set_strategy_parameters(row)

                current_price = row [self.strategy.instrument]
                trade_action = self.strategy.determine_action(current_price, current_price, self.have_units, self.units_to_trade)
                
        
                if trade_action != None:
                    if self.have_units == 0 and trade_action.units > 0:
                        # pl = pl - trade_action.units * trade_action.price
                        self.outstanding = -trade_action.units * trade_action.price
                        self.go_long = self.go_long + 1
                        # logger.info(f"Go Long -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
                    elif self.have_units == 0 and trade_action.units < 0:
                        # pl = pl - trade_action.units * trade_action.price
                        self.outstanding = -trade_action.units * trade_action.price
                        self.go_short = self.go_short + 1
                        # logger.info(f"Go Short -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
                    elif self.have_units > 0 and trade_action.units < 0:
                        # pl = pl - trade_action.units * trade_action.price
                        self.outstanding = self.outstanding - trade_action.units * trade_action.price
                        self.pl = self.pl + self.outstanding
                        self.close_long = self.close_long + 1
                        # logger.info(f"Close Long -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
                    elif self.have_units < 0 and trade_action.units > 0:
                        # pl = pl - trade_action.units * trade_action.price
                        self.outstanding = self.outstanding - trade_action.units * trade_action.price
                        self.pl = self.pl + self.outstanding
                        self.close_short = self.close_short + 1
                        # logger.info(f"Close Short -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
                    else:
                        logger.error(f"Error in calculating P&L - have_units: {self.have_units}, trade_action.units: {trade_action.units}, trade_action.price: {trade_action.price}")

                    self.have_units = self.have_units + trade_action.units
                    self.i = self.i + 1
                    self.trades.append([index, trade_action.units, trade_action.price, self.have_units, '${:,.2f}'.format(self.outstanding), '${:,.2f}'.format(self.pl)])
            
            self.print_metrics()

        except Exception as e:
            logger.exception("Exception occurred")
        finally:
            logger.info("Stopping Backtesting")
    
    def print_metrics(self):

            logger.info(f"Finished Trading Session with P&L: {'${:,.2f}'.format(self.pl)}, # of trades: {self.i}, have_units: {self.have_units}")
            logger.info(f"go long: {self.go_long}, go short: {self.go_short}, close long: {self.close_long}, close short: {self.close_short}")
       
            logger.info("\n" + 100 * "-")        
            if self.trades != None and len(self.trades) > 0:
                df = pd.DataFrame(data=self.trades, columns=["datetime", "trade units", "price", "new # of units", "trade p&l", "total p&l"])
                logger.info("\n" + df.to_string(header=True))
                logger.info("\n" + 100 * "-")


if __name__ == "__main__":
    # insert the file path of your config file below!

    args = sys.argv[1:]
    refresh = False
    pair = args[0]
    if len(args) > 1:
        refresh = bool(args[1])


    trader = SMA_to_BB_Back_Test(
        conf_file="../trading/oanda.cfg",
        pairs_file="../trading/pairs.ini",
        instrument=pair
    )
    trader.start_trading_backtest(refresh)

