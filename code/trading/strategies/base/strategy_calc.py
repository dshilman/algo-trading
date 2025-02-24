from math import log

from trading.utils.tech_indicators import (
    count_sma_crossover, calculate_rsi, calculate_slope, calculate_ema)
from trading.strategies.base.strategy_base import TradingStrategyBase
from trading.utils import utils
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))


logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""


class TradingStrategyCalc(TradingStrategyBase):
    def __init__(self, trading_strategy, pair_file, api=None, unit_test=False):

        super().__init__(trading_strategy=trading_strategy,pair_file=pair_file, api=api, unit_test=unit_test)

    def add_tickers(self, ticker_df: pd.DataFrame):

        # logger.debug(f"Adding tickers to dataframe: {ticker_df}")

        df = self.data.copy()
        df = pd.concat([df, ticker_df])
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')
        self.data = df.tail(self.SMA * 2)

        # logger.debug("After new tickers:\n" + df.iloc[-1:].to_string(header=True))

    def to_5_min_candles(self, ticker_data_list) -> pd.DataFrame:

        # Create DataFrame
        ticker_df: pd.DataFrame = pd.DataFrame(ticker_data_list, columns=["time", "mid", "bid", "ask"])

        # Ensure 'time' is in datetime format and set as index
        ticker_df["time"] = pd.to_datetime(ticker_df["time"], utc=True)
        ticker_df = ticker_df.set_index("time")
        # logger.info(f"Last price ticker update {ticker_df.index[-1]}")

        # Handle timezone
        if isinstance(ticker_df.index, pd.DatetimeIndex) and ticker_df.index.tz is not None:
            ticker_df.index = ticker_df.index.tz_convert(timezone.utc)

        # Resample to 1-minute intervals
        ticker_df = ticker_df.resample("1Min").last().ffill()

        # Create a new DataFrame
        df = pd.DataFrame(index=ticker_df.index)

        df["close"] = ticker_df["mid"]
        df["open"] = df["close"].shift(1)
        df["ask"] = ticker_df["ask"]
        df["bid"] = ticker_df["bid"]
        df["high"] = ticker_df["mid"].rolling(5, min_periods=1).max()
        df["low"] = ticker_df["mid"].rolling(5, min_periods=1).min()

        # Resample to 5-minute intervals and fill missing values
        df = df.resample("5min").last().ffill()

        # logger.info("after resample")
        # logger.info(f"Last candle time {df.index[-1]}")

        return df



    def calc_indicators(self):

        df: pd.DataFrame = self.data

        # DEV = self.DEV
        std_dev = self.DEV
        period_long = self.SMA
        period_short = self.period_short

        # Bollinger Band
        df["close"] = df["close"].fillna(0)
        # df["change_rate"] = df["close"].pct_change()
        # df["change_rate_1h"] = df["close"].pct_change(periods=period_short)
        df["std_dev"] = df["close"].rolling(period_long).std(numeric_only=True)
        df["std_dev_mean"] = df["std_dev"].rolling(period_short).mean(numeric_only=True)

       
        df["sma_long"] = df["close"].rolling(period_long).mean(numeric_only=True)

        # df['ema_short'] = df["close"].rolling(period_short).apply(lambda x: calculate_ema(S=x))
        df['ema_short'] = df["close"].ewm(span=period_short, adjust=False).mean()

        # df['ema_short_min'] = df['ema_short'].rolling(period_short).min()
        # df['ema_short_max'] = df['ema_short'].rolling(period_short).max()
                

        df["bb_lower"] = df["sma_long"] - df["std_dev"] * std_dev
        df["bb_upper"] = df["sma_long"] + df["std_dev"] * std_dev

        df["price_max"] = df["high"].rolling(period_short).max()
        df["price_min"] = df["low"].rolling(period_short).min()

        # Price/Volume Momentum
        # df["volume_pct_change"] = df["volume"].pct_change()
        # df["volume_max"] = df["volume"].rolling(period_short).max()
        # df["price_pct_change"] = df["close"].pct_change()
        # df["price_pct_max"] = df["price_pct_change"].rolling(period_short).max()
        # df ["trading_volatility"] = abs(df["price_pct_change"] / df["volume_pct_change"])
        # df['price_volatility'] =  abs(df['sma_long'] - df["close"]) / df['std_dev']

        # Lequidity
        # df["bid_ask_spread"] = (df["ask"] - df["bid"]) / df["close"]
        # df["effective_spread"] = (df["ask"] - df["bid"]) / (df["close"] * 2)
        # df["price_efficiency_short"] = df["close"].rolling(period_short).var()
        # df["price_efficiency_long"] = df["close"].rolling(period_long).var()

        # Volatility
        # df["price_diff"] = df["close"].diff()
        # df['volatility'] = df['price_diff'].rolling(window=period_short).std()

        # MACD
        # df["ema_long"] = df["close"].rolling(period_long).apply(lambda x: calculate_ema(S=x))
        # df['ema_long_slope'] = df["ema_long"].rolling(period_long).apply(lambda x: calculate_slope(x))

        # df['ema_short_slope'] = df["ema_short"].rolling(period_short).apply(lambda x: calculate_slope(x))

        # Momentum
        # df["price_momentum_long"] = df["price_diff"].rolling(period_long).sum()
        # df["price_momentum_long_min"] = df['price_momentum_long'].rolling(period_long).min()
        # df["price_momentum_long_max"] = df['price_momentum_long'].rolling(period_long).max()

        # df["price_momentum_short"] = df["price_diff"].rolling(period_short).sum()
        # df["price_momentum_short_min"] = df["price_momentum_short"].rolling(period_short).min()
        # df["price_momentum_short_max"] = df["price_momentum_short"].rolling(period_short).max()


        # RSI
        # df["rsi_long"] = df["close"].rolling(period_long).apply(lambda x: calculate_rsi(x, period_long))
        # df["rsi_long_prev"] = df.rsi_long.shift()
        # df["rsi_long_max"] = df['rsi_long'].rolling(period_long).max()
        # df["rsi_long_min"] = df['rsi_long'].rolling(period_long).min()

        df["rsi_short"] = df["close"].rolling(period_short).apply(lambda x: calculate_rsi(x, period_short))
        df["rsi_short_max"] = df["rsi_short"].rolling(period_short).max()
        df["rsi_short_min"] = df["rsi_short"].rolling(period_short).min()
        
        # df["price_pct_change"] = df["close"].pct_change(fill_method=None)
        # df["ema_short_pct_change"] = df["ema_short"].pct_change(fill_method=None)
        df["rsi_short_pct_change"] = df["rsi_short"].pct_change(fill_method=None)

        # df['price_slope'] = df["close"].rolling(period_short).apply(lambda x: calculate_slope(x))
        # df['ema_short_slope'] = df["ema_short"].rolling(period_short).apply(lambda x: calculate_slope(x))
        # df['rsi_short_slope'] = df["rsi_short"].rolling(period_short).apply(lambda x: calculate_slope(x))


        # df["rsi_short_pct_change_max"] = df.rsi_short_pct_change.rolling(period_short).max()
        # df["rsi_short_pct_change_min"] = df.rsi_short_pct_change.rolling(period_short).min()
   
        # df["rsi_diff"] = df.rsi.diff()
        # df["rsi_momentum_" + str(period)] = df["rsi_diff"].rolling(period).sum()
        # df["rsi_momentum_" + str(period) + "_max"] = df["rsi_momentum_" + str(period)].rolling(period).max()
        # df["rsi_momentum_" + str(period) + "_min"] = df["rsi_momentum_" + str(period)].rolling(period).min()
      
        # df["greater_sma"] = df["sma_long"] - df["ema_short"]
        # df["sma_crossover"] = df["greater_sma"].rolling(period_short).apply(lambda x: count_sma_crossover(x))

        # df.drop(columns=["greater_sma"], inplace=True)

        
        if self.unit_test:
            logger.info("\n" + df.tail(10).to_string(header=True))

        self.data = df

    def set_strategy_indicators(self, row: pd.Series):  # type: ignore

        logger.debug("Setting strategy indicators")

        if row is None:
            row = self.data.iloc[-1]
    
        self.ask = row["ask"]
        self.bid = row["bid"]
        self.price = row["close"]
        self.price_low = row["low"]
        self.price_high = row["high"]
        # self.change_rate_1h = row["change_rate_1h"]

        self.price_max = row["price_max"]
        self.price_min = row["price_min"]
        # self.price_volatility = row['price_volatility']
        # self.trading_volatility = row['trading_volatility']
        # self.price_efficiency_long = row['price_efficiency_long']
        # self.price_std = row['std_dev']
        self.std_dev = row["std_dev"]
        self.std_dev_mean = row["std_dev_mean"]

        # self.price_std_mean = row['price_std_mean']

        # MACD
        # self.ema_long = row["ema_long"]

        # Bollinger Band
        # self.sma_short = row['sma_short']
        self.sma_long = row['sma_long']
        self.ema_short = row["ema_short"]

        self.bb_low = row['bb_lower']
        self.bb_high = row['bb_upper']

        # self.sma_long_slope = row["sma_long_slope"]

        # self.ema_short_min = row["ema_short_min"]
        # self.ema_short_max = row["ema_short_max"]
        # # self.ema_short_slope = row["ema_short_slope"]
        # self.price_ema_short_slope_max = row["ema_short_slope_max"]
        # self.price_ema_short_slope_min = row["ema_short_slope_min"]

        # Momentum
        # self.price_momentum_long = row["price_momentum_long"]
        # self.price_momentum_long_min = row["price_momentum_long_min"]
        # self.price_momentum_long_max = row["price_momentum_long_max"]

        
        # self.price_momentum_short = row["price_momentum_short"]
        # self.price_momentum_long = row["price_momentum_long"]
        # self.price_momentum_short_min = row["price_momentum_short_min"]
        # self.price_momentum_short_max = row["price_momentum_short_max"]
        
        # self.price_momentum_short_mean = row["price_momentum_short_mean"]
        

        # RSI
        # self.rsi_long = round(row["rsi_long"], 4)
        # self.rsi_long_prev = round(row["rsi_long_prev"], 4)
        # self.rsi_long_max = round(row["rsi_long_max"], 4)
        # self.rsi_long_min = round(row["rsi_long_min"], 4)

        self.rsi_short = round(row["rsi_short"], 4)
        # self.rsi_short_pct_change_max = row["rsi_short_pct_change_max"]
        # self.rsi_short_pct_change_min = row["rsi_short_pct_change_min"]
        self.rsi_short_max = round(row["rsi_short_max"], 4)
        self.rsi_short_min = round(row["rsi_short_min"], 4)
        # self.rsi_short_ema = row["rsi_short_ema"]

        # self.price_slope = row["price_slope"]
        # self.ema_short_slope = row["ema_short_slope"]
        # self.rsi_short_slope = row["rsi_short_slope"]

        # self.price_pct_change = row["price_pct_change"]
        # self.ema_short_pct_change = row["ema_short_pct_change"]
        self.rsi_short_pct_change = row["rsi_short_pct_change"]

        # Volume Momentum
        # self.volume_momentum_short = row ["volume_momentum_short"]
        # self.volume_momentum_long = row ["volume_momentum_long"]
        # self.volume = row ["volume"]
        # self.volume_pct_change = row ["volume_pct_change"]
        # self.volume_max = row ["volume_max"]


        # self.sma_crossover = row ["sma_crossover"]
       
       
    def print_indicators(self):

        logger.info(f'price: {round(self.price, 6)}, std_dev: {round(self.std_dev, 6)}, bb_low: {round(self.bb_low, 6)}, bb_high: {round(self.bb_high, 6)}')
        logger.info(f'rsi: {round(self.rsi_short, 6)}, rsi_max: {round(self.rsi_short_max, 6)}, rsi_min: {round(self.rsi_short_min, 5)}, rsi_pct_change: {round(self.rsi_short_pct_change, 6)}')
        # logger.info("\n" + self.data.tail(5).to_string(header=True))
        # price_data = [[self.ask, self.bid, self.price, round(self.price_std, 6)]]
        # price_headers = ["ASK PRICE", "BID PRICE", "MID PRICE", "PRICE STD"]
        # logger.info("\n" + tabulate(price_data, headers=price_headers) + "\n")

        # logger.debug("*********** MACD and BOLLINGER *************")
        # macd_bb_data = [[self.price_ema_short, self.sma_long, self.bb_low, self.bb_high]]
        # macd_bb_headers = ["EMA SHORT", "SMA LONG", "BB_LOW", "BB_HIGH"]
        # logger.debug("\n" + tabulate(macd_bb_data, headers=macd_bb_headers) + "\n")

        # logger.debug("*********** MOMENTUM *************")
        # momentum_data = [[self.price_momentum_short]]
        # momentum_headers = ["PRICE MOMENTUME SHORT"]
        # logger.debug("\n" + tabulate(momentum_data, headers=momentum_headers) + "\n")

        # logger.debug("*********** RSI *************")
        # rsi_data = [[self.rsi_short, self.rsi_short_min, self.rsi_short_max]]
        # rsi_headers = ["RSI SHORT", "RSI SHORT MIN", "RSI SHORT MAX"]
        # logger.debug("\n" + tabulate(rsi_data, headers=rsi_headers) + "\n")

        # logger.debug("*********** VOLUME *************")
        # volume_momentume_data = [[self.volume, self.volume_pct_change, self.volume_max]]
        # volume_momentume_headers = ["VOLUME", "VOLUME % CHANGE", "VOLUME MAX"]
        # logger.debug("\n" + tabulate(volume_momentume_data, headers=volume_momentume_headers) + "\n")


    def get_open_trade_price(self):

        have_units = self.trading_session.have_units

        if have_units != 0 and len(self.trading_session.trades) > 0:
            trade:str = self.trading_session.trades[-1][2]
            if trade is not None and trade.startswith("Open"):
                open_trade_price = self.trading_session.trades[-1][5]
                return open_trade_price
        
        return None


    def is_trading_time(self, date_time: datetime) -> bool:

        logger.debug(f"Date time: {date_time}")

        day = date_time.weekday()
        hour = date_time.hour

        if day == 4 and hour >= 20:
            return False

        pause_from_dt = datetime.combine(date_time.date(), datetime.strptime(self.pause_start, '%H:%M:%S').time(), tzinfo=timezone.utc)
        pause_to_dt = datetime.combine(date_time.date(), datetime.strptime(self.pause_end, '%H:%M:%S').time(), tzinfo=timezone.utc)

        if pause_from_dt > pause_to_dt:
            pause_from_dt = pause_from_dt - pd.DateOffset(days=1)

        if pause_from_dt < date_time < pause_to_dt:
            return False

        return True

    def get_open_trade_time(self):

        date_time = None

        if len(self.trading_session.trades) > 0:
            trade:str = self.trading_session.trades[-1][2]
            if trade.startswith("Open"):
                date_time = self.trading_session.trades[-1][0]

        return date_time