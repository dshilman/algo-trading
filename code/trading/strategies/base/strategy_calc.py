from math import log

from trading.utils.tech_indicators import (
    count_sma_crossover, calculate_rsi, calculate_slope, calculate_ema)
from trading.strategies.base.strategy_base import TradingStrategyBase
from trading.utils import utils
import logging
import sys
import math
from datetime import datetime, timedelta, timezone
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

    
    def to_5_min_candles(self, ticker_data_list, trading_time) -> pd.DataFrame:

        # Create DataFrame
        filtered_ticker_data_list = [item for item in ticker_data_list if item[0] >= trading_time - timedelta(minutes=utils.ticker_data_size * 5)]

        ticker_df: pd.DataFrame = pd.DataFrame(filtered_ticker_data_list, columns=["time", "mid", "bid", "ask"])

        # Ensure "time" is in datetime format and set as index
        ticker_df["time"] = pd.to_datetime(ticker_df["time"], utc=True)
        ticker_df = ticker_df.set_index("time")

        # Handle timezone
        if isinstance(ticker_df.index, pd.DatetimeIndex) and ticker_df.index.tz is None:
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

        logger.info(f"price data queue size: {len(ticker_data_list)}, filtered price data size: {len(filtered_ticker_data_list)},  ticker data size: {len(df.index)}")

        return df

    def calc_indicators(self):

        df: pd.DataFrame = self.data

        # DEV = self.DEV
        std_dev_long = self.DEV
        period_long = self.SMA
        period_short = self.period_short

        # Bollinger Band
        df["close"] = df["close"].fillna(0)
        df["std_dev_long"] = df["close"].rolling(period_long).std(numeric_only=True)
        df["price_volatility"] = ((df["high"] - df["low"]) / (df["high"] + df["low"]) / 2).rolling(self.period_short).mean()    
        df["sma_long"] = df["close"].rolling(period_long).mean(numeric_only=True)
        df["ema_short"] = df["close"].ewm(span=period_short, adjust=False).mean()
        df["bb_lower"] = df["sma_long"] - df["std_dev_long"] * std_dev_long
        df["bb_upper"] = df["sma_long"] + df["std_dev_long"] * std_dev_long
        df["price_max"] = df["high"].rolling(period_short).max()
        df["price_min"] = df["low"].rolling(period_short).min()
        df["rsi_short"] = df["close"].rolling(period_short).apply(lambda x: calculate_rsi(x, period_short))
        df["rsi_short_max"] = df["rsi_short"].rolling(period_short).max()
        df["rsi_short_min"] = df["rsi_short"].rolling(period_short).min()
        df["rsi_short_pct_change"] = df["rsi_short"].pct_change(fill_method=None).rolling(3).sum() # type: ignore

        df["macd_crossover"] = 0  # Initialize signal column
        df.loc[(df["ema_short"].shift() < df["sma_long"]) & (df["ema_short"] > df["sma_long"]), "macd_crossover"] = 1  # Bullish crossover
        df.loc[(df["ema_short"].shift() > df["sma_long"]) & (df["ema_short"] < df["sma_long"]), "macd_crossover"] = -1  # Bearish crossover
        df["macd_crossover"] = df["macd_crossover"].rolling(5).sum()

        df["bb_crossover"] = 0  # Initialize signal column
        df.loc[(df["ema_short"].shift() < df["bb_lower"].shift()) & (df["ema_short"] > df["bb_lower"]), "bb_crossover"] = 1  # Bullish crossover
        df.loc[(df["ema_short"].shift() > df["bb_upper"].shift()) & (df["ema_short"] < df["bb_upper"]), "bb_crossover"] = -1  # Bearish crossover
        df["bb_crossover"] = df["bb_crossover"].rolling(2).sum()

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
        self.price_open = row["open"]
        self.price_low = row["low"]
        self.price_high = row["high"]
        self.price_max = row["price_max"]
        self.price_min = row["price_min"]
        self.std_dev_long = row["std_dev_long"]
        self.price_volatility = row["price_volatility"]
        self.sma_long = row["sma_long"]
        self.ema_short = row["ema_short"]
        self.bb_low = row["bb_lower"]
        self.bb_high = row["bb_upper"]
        self.rsi_short = round(row["rsi_short"], 4)
        self.rsi_short_max = round(row["rsi_short_max"], 4)
        self.rsi_short_min = round(row["rsi_short_min"], 4)
        self.rsi_short_pct_change = row["rsi_short_pct_change"]
        self.macd_crossover = row["macd_crossover"]
        self.bb_crossover = row["bb_crossover"]
               
       
    def print_indicators(self):

        logger.info(f"price: {round(self.price, 6)}, std_dev_long: {round(self.std_dev_long, 6)}, price_volatility: {round(self.price_volatility, 5)}, price_min: {round(self.price_min, 6)}, price_max: {round(self.price_max, 6)}")
        logger.info(f"sma_long: {round(self.sma_long, 6)} bb_low: {round(self.bb_low, 6)}, bb_high: {round(self.bb_high, 6)}, ema_short: {round(self.ema_short, 6)}")
        logger.info(f"rsi_short: {round(self.rsi_short, 2)}, rsi_max: {round(self.rsi_short_max, 2)}, rsi_min: {round(self.rsi_short_min, 2)}, rsi_pct_change: {round(self.rsi_short_pct_change, 2)}")
        logger.info(f"macd_crossover: {self.macd_crossover}, bb_crossover: {self.bb_crossover}")

