import configparser
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from dateutil import parser
import yfinance as yf


file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from dom.order import Order
from utils import utils

logger = logging.getLogger()


class yfinanceApi:

    def __init__(self):
        print("Init")
    
    def __format(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.drop(columns=["Open", "High", "Low", "Dividends", "Stock Splits"])
        df.rename(columns={"Close": "close"})
        return df

    def get_latest_price_candles(self, instrument) -> pd.DataFrame:
        
        ticker = yf.Ticker(instrument)
        df = ticker.history(start=datetime.now().strftime('%Y-%m-%d') ,interval="1m")
        df = self.__format(df)
        
        return df



    def get_price_candles(self, instrument, days = 1):

        start = datetime.now()
        end = start - timedelta(days=days)

        
        df = pd.DataFrame()
        ticker = yf.Ticker(instrument)

        if days == 1:
            logger.debug(f"Getting price candles for {instrument} from {start} to {end}")
            df = ticker.history(start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), interval="1m")
        else:
            for i in range(0, days):

                start = end
                end = start + timedelta(days=i+1)
                if end.weekday() < 5:
                    logger.debug(f"Getting price candles for {instrument} from {start} to {end}")
                    df_t = ticker.history(start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), interval="1m")

                    if not df_t.empty:
                        df = pd.concat([df, df_t])

        if not df.empty:
            df = self.__format(df)

        return df



if __name__ == "__main__":
    api = yfinanceApi()
    df = api.get_price_candles("TSLA", 4)
    print(df)
    print ("Done!")

# python yfinance_api.py