import configparser
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from dateutil import parser

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from dom.order import Order
from utils import utils

from polygon import RESTClient

logger = logging.getLogger()


class PolygonAPI:

    def __init__(self):
        self.client = RESTClient(api_key="iSJWcq8jWhe3Bmw7K0Fc19hoctpwvABc", trace=True)

    def get_latest_price_candles(self, ticker) -> pd.DataFrame:

        # List Quotes
        quotes = self.client.list_quotes(ticker=ticker)
        for quote in quotes:
            print(quote)


    def get_price_candles(self, pair_name, days = 0, hours = 0, minutes = 0, seconds = 0):
        pass



if __name__ == "__main__":
    api = PolygonAPI().get_latest_price_candles("KTKG")
    print ("Done!")

# python polygon_api.py