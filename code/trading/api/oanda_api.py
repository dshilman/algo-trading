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

logger = logging.getLogger()


class OandaApi:

    def __init__(self, config_file):
        self.session = requests.Session()

        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.access_token = self.config['oanda']['access_token']
        self.account_id = self.config['oanda']['account_id']
        self.account_type = self.config['oanda']['account_type']

        if self.account_type == 'live':
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
            granularity="S30",
            price="MBA",
            count=utils.ticker_data_size
        )

        ok, data = self.__make_request(url, params=params)

        if ok and 'candles' in data:
            # logger.info(f"Candles: {data['candles']}")
            df = self.__convert_to_df(data['candles'])
            df = df.set_index('time')
            df.index = df.index.tz_localize(None)
            return df
        else:
            print("ERROR fetch_candles()", params, data)
            return None



    def get_price_candles(self, pair_name, days = 0, hours = 0, minutes = 0, seconds = 0):

        now = datetime.now(tz=timezone.utc)
        now = now - timedelta(seconds=now.second, microseconds=now.microsecond)
        past = now - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

        df = pd.DataFrame()

        if days == 0:
            logger.debug(f"Getting price candles for {pair_name} from {past} to {now}")
            data_t: pd.DataFrame = self.__fetch_candles(date_f=past, date_t=now, pair_name=pair_name, granularity="S30", price="MBA")
            df = self.__convert_to_df(data_t)
        else:
            for i in range(0, days):

                start_d = past + timedelta(days=i)
                end_d = start_d + timedelta(days=1)

                logger.debug(f"Getting price candles for {pair_name} from {start_d} to {end_d}")
                data_t: pd.DataFrame = self.__fetch_candles(date_f=start_d, date_t=end_d, pair_name=pair_name, granularity="S30", price="MBA")
                df_t = self.__convert_to_df(data_t)
                df = pd.concat([df, df_t])

        df = df.set_index('time')
        df.index = df.index.tz_localize(None)

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

        if order.sl is not None:
            stopLossOnFill = dict(price=str(order.sl))
            data['order']['stopLossOnFill'] = stopLossOnFill

        if order.tp is not None:
            takeProfitOnFill = dict(price=str(order.tp))
            data['order']['takeProfitOnFill'] = takeProfitOnFill

        ok, response = self.__make_request(
            url, verb="post", data=data, code=201)

        if ok:
            result = None
            if 'orderRejectTransaction' in response:
                result = response.get('orderRejectTransaction')
            elif 'orderFillTransaction' in response:
                result = response.get('orderFillTransaction')
            elif 'orderCreateTransaction' in response:
                result = response.get('orderCreateTransaction')
            
            return result
        
        return None


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
        
        print(f"Instrument: {kwargs.get('instrument')} | Time: {kwargs.get('time')} | \
            Bid: {kwargs.get('bid')} | \
                Ask: {kwargs.get('ask')} | \
                    Status: {kwargs.get('status')}")

    def __handle_response(self, response, callback, stop):

        count = 0
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                # print (data)
                if data.get("type") == "PRICE":
                    count += 1
                    instrument = data["instrument"]
                    time = data["time"]
                    bid = float(data["closeoutBid"])
                    ask = float(data["closeoutAsk"])
                    status = data["status"]                    
                    if callback and status:
                        callback(instrument=instrument, time=time, bid=bid, ask=ask, status=status)
                    else:
                        self.__on_success(instrument=instrument, time=time, bid=bid, ask=ask, status=status)
                
                    if self.stop_stream or stop is not None and count >= stop:
                        break

        return

    def __make_request(self, url, verb='get', code=200, params=None, data=None, headers=None):
        full_url = f"{self.hostname}/{url}"

        if data is not None:
            data = json.dumps(data)

        try:
            response = None
            if verb == "get":
                response = self.session.get(
                    full_url, params=params, data=data, headers=headers)
            if verb == "post":
                response = self.session.post(
                    full_url, params=params, data=data, headers=headers)
            if verb == "put":
                response = self.session.put(
                    full_url, params=params, data=data, headers=headers)

            if response == None:
                return False, {'error': 'verb not found'}

            if response.status_code == code:
                return True, response.json()
            else:
                return False, response.json()

        except Exception as error:
            return False, {'Exception': error}

    def __fetch_candles(self, pair_name, date_f, date_t, granularity="S30", price="MBA") -> pd.DataFrame:

        url = f"instruments/{pair_name}/candles"
        params = dict(
            granularity=granularity,
            price=price
        )

        date_format = "%Y-%m-%dT%H:%M:%SZ"
        params["from"] = datetime.strftime(date_f, date_format)
        params["to"] = datetime.strftime(date_t, date_format)

        ok, data = self.__make_request(url, params=params)

        if ok and 'candles' in data:
            # logger.info(f"Candles: {data['candles']}")
            return data['candles']
        else:
            print("ERROR fetch_candles()", params, data)
            return None

    def __convert_to_df(self, data):

        if data is None:
            return None

        if len(data) == 0:
            return pd.DataFrame()

        prices = ['mid', 'bid', 'ask']

        final_data = []
        for candle in data:
            # if not candle["complete"]:
            #     continue
            
            new_dict = {}
            new_dict['time'] = parser.parse(candle['time'])
            new_dict['volume'] = candle['volume']
            
            for p in prices:
                if p in candle:
                    new_dict[f"{p}"] = float(candle[p]["c"])
                    # if p == 'mid':
                    #     new_dict[f"{p}_o"] = float(candle[p]["o"])

            final_data.append(new_dict)

        df = pd.DataFrame.from_dict(final_data)
        df.rename(columns={"mid": "close"}, inplace=True)
        return df

if __name__ == "__main__":
    api = OandaApi("../../../config/oanda.cfg")
    api.stream_prices(instrument="EUR_USD", stop = 5)
    print ("Done!")

# python oanda_api.py