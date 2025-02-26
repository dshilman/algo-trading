import configparser
import json
import logging
from logging import handlers
from math import log
import os
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

logger = logging.getLogger()


class OandaApi:

    def __init__(self, config_file):
        self.session = requests.Session()

        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.access_token = self.config["oanda"]["access_token"]
        self.account_id = self.config["oanda"]["account_id"]
        self.account_type = self.config["oanda"]["account_type"]

        if self.account_type == "live":
            self.hostname = "https://api-fxtrade.oanda.com/v3"
            self.stream_hostname = "https://stream-fxtrade.oanda.com/v3"
        else:
            self.hostname = "https://api-fxpractice.oanda.com/v3"
            self.stream_hostname = "https://stream-fxpractice.oanda.com/v3"

        self.SECURE_HEADER = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        self.session.headers.update(self.SECURE_HEADER)
        self.stop_stream = False

    def get_latest_price_candles(self, pair_name) -> pd.DataFrame:

        url = f"accounts/{self.account_id}/candles/latest"
        params = dict(
            instrument=pair_name,
            granularity="M5",
            price="MBA",
            count=utils.ticker_data_size
        )

        ok, data = self.__make_request(url, params=params)

        df: pd.DataFrame = pd.DataFrame()
        if ok and "candles" in data:
            logger.debug(f"Latest price candles for {pair_name}:\n{data["candles"]}")

            if isinstance(data, dict) and "candles" in data:
                df = self.__convert_to_df(data["candles"]) # type: ignore
                df = df.set_index("time")
                if isinstance(df.index, pd.DatetimeIndex):
                    df.index = df.index.tz_convert(tz=timezone.utc)
                logger.debug(f"Latest price candles for {pair_name}:\n{df}")
                return df
            else:
                logger.debug("ERROR converting candles to DataFrame", data["candles"])
                return df
        else:
            logger.error("ERROR fetch_candles()", params, data)
            return df



    def get_price_candles(self, pair_name, days = 0, hours = 0, minutes = 0, seconds = 0):

        now = datetime.now(tz=timezone.utc)
        now = now - timedelta(seconds=now.second, microseconds=now.microsecond)
        past = now - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

        df = pd.DataFrame()

        if days == 0:
            logger.debug(f"Getting price candles for {pair_name} from {past} to {now}")
            data_t: dict = self.__fetch_candles(date_f=past, date_t=now, pair_name=pair_name, granularity="M5", price="MBA")

            df = self.__convert_to_df(data_t)
        else:
            for i in range(0, days):

                start_d = past + timedelta(days=i)
                end_d = start_d + timedelta(days=1)

                logger.debug(f"Getting price candles for {pair_name} from {start_d} to {end_d}")
                data_t: dict = self.__fetch_candles(date_f=start_d, date_t=end_d, pair_name=pair_name, granularity="M5", price="MBA")
                df_t = self.__convert_to_df(data_t)
                df = pd.concat([df, df_t])

        df = df.set_index("time")
        if isinstance(df.index, pd.DatetimeIndex):
            df.index = df.index.tz_convert(timezone.utc)

        return df

    def place_order(self, order: Order):

        url = f"accounts/{self.account_id}/orders"

        data = dict(
            order=dict(
                units=str(order.units),
                instrument=order.instrument,
                type="MARKET",
                positionFill="DEFAULT",
                timeInForce="FOK"
            )
        )

        if order.trailing_sl is not None:
            trailingStopLossOnFill = dict(distance=str(order.trailing_sl))
            data['order']['trailingStopLossOnFill'] = trailingStopLossOnFill # type: ignore
        elif order.sl is not None:
            stopLossOnFill = dict(price=str(order.sl))
            data['order']['stopLossOnFill'] = stopLossOnFill # type: ignore
        if order.tp is not None:
            takeProfitOnFill = dict(price=str(order.tp))
            data['order']['takeProfitOnFill'] = takeProfitOnFill # type: ignore

        ok, response = self.__make_request(url, verb="post", data=data, code=201)

        if ok:
            result = None
            if "orderRejectTransaction" in response:
                result = response.get("orderRejectTransaction")
            elif "orderFillTransaction" in response:
                result = response.get("orderFillTransaction")
            elif "orderCreateTransaction" in response:
                result = response.get("orderCreateTransaction")
            
            return result
        
        else:
            logger.error(f"ERROR in place_order(). status: {ok}, request: {data}, response: {response}")
        

    def get_position(self, instrument): 

        units = 0
        url = f"accounts/{self.account_id}/positions/{instrument}"
        ok, data = self.__make_request(url, verb="get", code=200)
        if ok and "position" in data:
            long_units = data["position"]["long"]["units"] # type: ignore
            short_units = data["position"]["short"]["units"] # type: ignore
            # logger.info (f"Currently have position: {instrument} | long_units: {long_units} | short_units: {short_units}")
            units = round(float(long_units) + float(short_units), 0)

        return units

    def stop_streaming(self):
        self.stop_stream = True

    def stream_prices(self, instrument, callback=None, stop=None):

        self.stop_stream = False

        url = f"accounts/{self.account_id}/pricing/stream"
        params = dict(instruments=instrument, snapshot=True)

        # Make the request
        response = self.session.request(url=f"{self.stream_hostname}/{url}", method = "get", params=params, stream=True)

        # Handle the streaming response
        result = self.__handle_response(response, callback, stop)

        return result
    def __on_success(self, **kwargs):
        
        logger.debug(f"Instrument: {kwargs.get("instrument")} | Time: {kwargs.get("time")} | \
            Bid: {kwargs.get("bid")} | \
                Ask: {kwargs.get("ask")}")

    def __handle_response(self, response, callback, stop):

        count = 0
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                logger.debug (data)
                if data.get("type") == "PRICE":
                    count += 1
                    instrument = data["instrument"]
                    time = data["time"]
                    if len(data["bids"]) > 0:
                        bid = float(data["bids"][0]["price"])
                    else: 
                        bid = float(data["closeoutBid"])

                    if len(data["asks"]) > 0:
                        ask = float(data["asks"][0]["price"])
                    else: 
                        ask = float(data["closeoutAsk"])

                    if callback:
                        callback(instrument=instrument, time=time, bid=bid, ask=ask)
                    else:
                        self.__on_success(instrument=instrument, time=time, bid=bid)
                
                    if self.stop_stream or stop is not None and count >= stop:
                        break

        return

    def __make_request(self, url, verb="get", code=200, params=None, data=None, headers=None):
        
        full_url = f"{self.hostname}/{url}"

        if data is not None:
            data = json.dumps(data)

        try:
            response = None
            if verb == "get":
                response = self.session.get(full_url, params=params, data=data, headers=headers)
            if verb == "post":
                response = self.session.post(full_url, params=params, data=data, headers=headers)
            if verb == "put":
                response = self.session.put(full_url, params=params, data=data, headers=headers)

            if response == None:
                return False, {"error": "verb not found"}

            if response.status_code == code:
                return True, response.json()
            else:
                return False, response.json()

        except Exception as error:
            return False, {"Exception": error}

    def __fetch_candles(self, pair_name, date_f, date_t, granularity="M5", price="MBA") -> dict:

        url = f"instruments/{pair_name}/candles"
        params = dict(
            granularity=granularity,
            price=price
        )

        date_format = "%Y-%m-%dT%H:%M:%SZ"
        params["from"] = datetime.strftime(date_f, date_format)
        params["to"] = datetime.strftime(date_t, date_format)

        ok, data = self.__make_request(url, params=params)

        if ok and "candles" in data:
            # logger.info(f"Candles: {data["candles"]}")
            return data["candles"] # type: ignore
        else:
            logger.debug("ERROR fetch_candles()", params, data)
            return {}

    def __convert_to_df(self, data: dict)-> pd.DataFrame:

        if data is None:
            return None

        if len(data) == 0:
            return pd.DataFrame()

        prices = ["mid", "bid", "ask"]

        final_data = []
        for candle in data:
            # if not candle["complete"]:
            #     continue
            
            new_dict = {}
            new_dict["time"] = parser.parse(candle["time"])
            new_dict["volume"] = candle["volume"]
            
            for p in prices:
                if p in candle:
                    if p == "mid":
                       new_dict["open"] = float(candle[p]["o"])
                       new_dict["close"] = float(candle[p]["c"])
                       new_dict["high"] = float(candle[p]["h"])
                       new_dict["low"] = float(candle[p]["l"])
                    else:
                        new_dict[f"{p}"] = float(candle[p]["c"])


            final_data.append(new_dict)

        df = pd.DataFrame(final_data)
        return df

if __name__ == "__main__":
    api = OandaApi("../../../config/oanda.cfg")
    logger.setLevel(logging.DEBUG)     
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", utils.date_format)

    log_dir = os.path.join(os.path.dirname(__file__), "../../../logs/trading")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"oanda_api.log")
    log_handler = handlers.RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)       
    order = Order(
            instrument = "EUR_USD",
            price =1.04876,
            trade_units = 100,
            sl_price = utils.convert_perc_to_ls_price(100, 0.0025, 1.04919),
            trailing_sl = utils.convert_perc_to_pips(100, 0.0025, 1.04919),
            tp_price = utils.convert_perc_to_tp_price(100, 0.0035, 1.04919)
        )
    data = api.place_order(order)
    logger.debug(data)
    logger.debug ("Done!")

# python oanda_api.py