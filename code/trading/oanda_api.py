import requests
import pandas as pd
import json
import configparser
from dateutil import parser
from datetime import datetime as dt


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
            self.stream_hostname = "stream-fxtrade.oanda.com"
        else:
            self.hostname = "https://api-fxpractice.oanda.com/v3"
            self.stream_hostname = "stream-fxpractice.oanda.com"

        SECURE_HEADER = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        self.session.headers.update(SECURE_HEADER)

    def make_request(self, url, verb='get', code=200, params=None, data=None, headers=None):
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

    def fetch_candles(self, pair_name, count=10, granularity="S30",
                      price="MBA", date_f=None, date_t=None):
        url = f"instruments/{pair_name}/candles"
        params = dict(
            granularity=granularity,
            price=price
        )

        if date_f is not None and date_t is not None:
            date_format = "%Y-%m-%dT%H:%M:%SZ"
            params["from"] = dt.strftime(date_f, date_format)
            params["to"] = dt.strftime(date_t, date_format)
        else:
            params["count"] = count

        ok, data = self.make_request(url, params=params)

        if ok == True and 'candles' in data:
            return data['candles']
        else:
            print("ERROR fetch_candles()", params, data)
            return None

    def get_candles_df(self, pair_name, **kwargs):

        data = self.fetch_candles(pair_name, **kwargs)

        if data is None:
            return None
        if len(data) == 0:
            return pd.DataFrame()

        prices = ['mid', 'bid', 'ask']
        ohlc = ['c']

        final_data = []
        for candle in data:
            if candle['complete'] == False:
                continue
            new_dict = {}
            new_dict['time'] = parser.parse(candle['time'])
            # new_dict['volume'] = candle['volume']
            for p in prices:
                if p in candle:
                    for o in ohlc:
                        new_dict[f"{p}_{o}"] = float(candle[p][o])
            final_data.append(new_dict)
        df = pd.DataFrame.from_dict(final_data)
        return df

    def last_complete_candle(self, pair_name, granularity):
        df = self.get_candles_df(pair_name, granularity=granularity, count=10)
        if df.shape[0] == 0:
            return None
        return df.iloc[-1].time

    def place_trade(self, instrument: str, units: int, stop_loss: float = None, take_profit: float = None):

        url = f"accounts/{self.account_id}/orders"

        data = dict(
            order=dict(
                units=str(units),
                instrument=instrument,
                type="MARKET"
            )
        )

        if stop_loss is not None:
            sld = dict(price=str(round(stop_loss, 4)))
            data['order']['stopLossOnFill'] = sld

        if take_profit is not None:
            tpd = dict(price=str(round(take_profit, 4)))
            data['order']['takeProfitOnFill'] = tpd

        ok, response = self.make_request(url, verb="post", data=data, code=201)

        if ok == True and 'orderFillTransaction' in response:
            return response['orderFillTransaction']['id']
        else:
            return None

    def close_trade(self, trade_id):
        url = f"accounts/{self.account_id}/trades/{trade_id}/close"
        ok, _ = self.make_request(url, verb="put", code=200)

        if ok == True:
            print(f"Closed {trade_id} successfully")
        else:
            print(f"Failed to close {trade_id}")

        return ok
