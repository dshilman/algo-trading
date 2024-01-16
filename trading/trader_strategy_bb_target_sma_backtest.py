import configparser
import logging
import logging.handlers as handlers
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from trader import Trade_Action
from trader_strategy_bb_target_sma import BB_to_SMA_Strategy

logger = logging.getLogger("back_tester")

class Trader_Back_Test():
    
    def __init__(self, pairs_file, instrument):
        
        self.strategy = BB_to_SMA_Strategy(instrument, pairs_file)
        config = configparser.ConfigParser()  
        config.read(pairs_file)
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        logger.setLevel(logging.INFO)

        log_file = os.path.join("logs", "backtester_" + instrument + ".log")
        logHandler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)

    
    def start_trading_backtest(self):

        logger.info("\n" + 100 * "-")

        try:
            have_units = 0
            pl = 0
            df = pd.read_excel(f"../explore/output_{self.strategy.instrument}.xlsx")
            df.reset_index(inplace=True)
            df.set_index('time', inplace=True)    
            df.drop(columns=['index'], inplace=True)

            for index, row in df.iterrows():
                self.strategy.rsi_max = row ['rsi_max']
                self.strategy.rsi_min = row ['rsi_min']
                current_price = row [self.strategy.instrument]
                self.strategy.bb_lower = row ['Lower']
                self.strategy.bb_upper =  row ['Upper']
                self.strategy.target = row ['SMA']
                self.strategy.rsi = row ['RSI']

                trade_action = self.strategy.determine_action(current_price, current_price, have_units, self.units_to_trade)
                
                if trade_action != None:
                    if have_units == 0 and trade_action.units > 0:
                        pl = pl - trade_action.units * trade_action.price
                    elif have_units == 0 and trade_action.units < 0:
                        pl = pl + trade_action.units * trade_action.price
                    elif have_units > 0 and trade_action.units < 0:
                        pl = pl - trade_action.units * trade_action.price
                    elif have_units < 0 and trade_action.units > 0:
                        pl = pl + trade_action.units * trade_action.price
                    else:
                        logger.error(f"Error in calculating P&L - have_units: {have_units}, trade_action.units: {trade_action.units}, trade_action.price: {trade_action.price}")

                    have_units =+ trade_action.units


 
            logger.info(f"Finished Trading Session with P&L: {pl}, have_units: {have_units}")
            logger.info("\n" + 100 * "-")
            
        except Exception as e:
            logger.exception("Exception occurred")
        finally:
            logger.info("Stopping Backtesting")
    


if __name__ == "__main__":
    # insert the file path of your config file below!

    args = sys.argv[1:]

    pair = args[0]


    trader = Trader_Back_Test(
        pairs_file="pairs.ini",
        instrument=pair
    )
    trader.start_trading_backtest()

