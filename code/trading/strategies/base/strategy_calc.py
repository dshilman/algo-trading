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
    def __init__(self, instrument, pair_file, api=None, unit_test=False):
        super().__init__(instrument=instrument,
                         pair_file=pair_file, api=api, unit_test=unit_test)

    def add_tickers(self, ticker_df: pd.DataFrame):

        # logger.debug(f"Adding tickers to dataframe: {ticker_df}")

        df = self.data.copy()
        df = pd.concat([df, ticker_df])
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')
        self.data = df.tail(self.SMA * 2)

        # logger.debug("After new tickers:\n" + df.iloc[-1:].to_string(header=True))

    def calc_indicators(self):

        df: pd.DataFrame = self.data

        instrument = self.instrument

        # DEV = self.DEV
        std_dev = 2
        period_long = 200
        period_short = 30

        # Bollinger Band
        df["std_dev"] = df[instrument].rolling(period_long).std()
        df["sma_long"] = df[instrument].rolling(period_long).mean()
        df['ema_short'] = df[instrument].rolling(period_short).apply(lambda x: calculate_ema(S=x))
        df['ema_short_slope'] = df["ema_short"].rolling(period_short).apply(lambda x: calculate_slope(x))

        df["bb_lower"] = df["sma_long"] - df["std_dev"] * std_dev
        df["bb_upper"] = df["sma_long"] + df["std_dev"] * std_dev

        # Price/Volume Momentum
        # df["volume_pct_change"] = df["volume"].pct_change()
        # df["volume_max"] = df["volume"].rolling(period_short).max()
        # df["price_pct_change"] = df[instrument].pct_change()
        # df["price_pct_max"] = df["price_pct_change"].rolling(period_short).max()
        # df ["trading_volatility"] = abs(df["price_pct_change"] / df["volume_pct_change"])
        # df['price_volatility'] =  abs(df['sma_long'] - df[instrument]) / df['std_dev']

        # Lequidity
        # df["bid_ask_spread"] = (df["ask"] - df["bid"]) / df[instrument]
        # df["effective_spread"] = (df["ask"] - df["bid"]) / (df[instrument] * 2)
        # df["price_efficiency_short"] = df[instrument].rolling(period_short).var()
        # df["price_efficiency_long"] = df[instrument].rolling(period_long).var()

        # Volatility
        # df["price_diff"] = df[instrument].diff()
        # df['volatility'] = df['price_diff'].rolling(window=period_short).std()

        # MACD
        # df["ema_long"] = df[instrument].rolling(period_long).apply(lambda x: calculate_ema(S=x))
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
        # df["rsi_long"] = df[instrument].rolling(period_long).apply(lambda x: calculate_rsi(x, period_long))
        # df["rsi_long_prev"] = df.rsi_long.shift()
        # df["rsi_long_max"] = df['rsi_long'].rolling(period_long).max()
        # df["rsi_long_min"] = df['rsi_long'].rolling(period_long).min()

        df["rsi_short"] = df[instrument].rolling(period_short).apply(lambda x: calculate_rsi(x, period_short))
        # df["rsi_short_prev"] = df["rsi_short"].shift()
        df["rsi_short_max"] = df.rsi_short.rolling(period_short).max()
        df["rsi_short_min"] = df.rsi_short.rolling(period_short).min()
        # df["rsi_short_pct_change"] = df.rsi_short.pct_change()
        # df["rsi_short_pct_change_max"] = df.rsi_short_pct_change.rolling(period_short).max()
        # df["rsi_short_pct_change_min"] = df.rsi_short_pct_change.rolling(period_short).min()
   
        # df["rsi_diff"] = df.rsi.diff()
        # df["rsi_momentum_" + str(period)] = df["rsi_diff"].rolling(period).sum()
        # df["rsi_momentum_" + str(period) + "_max"] = df["rsi_momentum_" + str(period)].rolling(period).max()
        # df["rsi_momentum_" + str(period) + "_min"] = df["rsi_momentum_" + str(period)].rolling(period).min()

        # df['rsi_ema'] = df["rsi"].rolling(period).apply(lambda x: calculate_ema(S = x, span = period))
        # df['rsi_ema_slope'] = df["rsi_ema"].rolling(period).apply(lambda x: calculate_slope(x))
        # df["rsi_ema_slope_max"] = df['rsi_ema_slope'].rolling(period).max()
        # df["rsi_ema_slope_min"] = df['rsi_ema_slope'].rolling(period).min()

        df["price_max"] = df[instrument].rolling(period_long).max()
        df["price_min"] = df[instrument].rolling(period_long).min()

        df["greater_sma"] = df["sma_long"] - df[instrument]
        df["greater_sma"] = df["greater_sma"].apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
        df["sma_crossover"] = df["greater_sma"].rolling(period_short).apply(lambda x: count_sma_crossover(x))

        df.drop(columns=["greater_sma"], inplace=True)

        
        if self.unit_test:
            logger.info("\n" + df.tail(10).to_string(header=True))

        self.data = df

    def set_strategy_indicators(self, row: pd.Series = None):  # type: ignore

        logger.debug("Setting strategy indicators")

        if row is None:
            row = self.data.iloc[-1]
    
        self.ask = row["ask"]
        self.bid = row["bid"]
        self.price = row[self.instrument]
        self.price_max = row["price_max"]
        self.price_min = row["price_min"]
        # self.price_volatility = row['price_volatility']
        # self.trading_volatility = row['trading_volatility']
        # self.price_efficiency_long = row['price_efficiency_long']
        self.price_std = row['std_dev']
        # self.price_std_mean = row['price_std_mean']

        # MACD
        # self.ema_long = row["ema_long"]

        # Bollinger Band
        self.sma_long = row['sma_long']
        self.bb_low = row['bb_lower']
        self.bb_high = row['bb_upper']

        # self.price_sma_long_slope = row["sma_long_slope"]
        # self.price_ema_long_slope = row["ema_long_slope"]
        self.ema_short = row["ema_short"]
        self.ema_short_slope = row["ema_short_slope"]
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
        # self.rsi_short_prev = round(row["rsi_short_prev"], 4)
        # self.rsi_short_pct_change = row["rsi_short_pct_change"]
        # self.rsi_short_pct_change_max = row["rsi_short_pct_change_max"]
        # self.rsi_short_pct_change_min = row["rsi_short_pct_change_min"]
        self.rsi_short_max = round(row["rsi_short_max"], 4)
        self.rsi_short_min = round(row["rsi_short_min"], 4)

        
        # Volume Momentum
        # self.volume_momentum_short = row ["volume_momentum_short"]
        # self.volume_momentum_long = row ["volume_momentum_long"]
        # self.volume = row ["volume"]
        # self.volume_pct_change = row ["volume_pct_change"]
        # self.volume_max = row ["volume_max"]


        self.sma_crossover = row ["sma_crossover"]

        self.trading = True
        if not self.backtest and "status" in row:
            self.trading = row["status"] == "tradeable"

       
       
    def print_indicators(self):

        price_data = [[self.ask, self.bid, self.price, round(self.price_std, 6)]]
        price_headers = ["ASK PRICE", "BID PRICE", "MID PRICE", "PRICE STD"]
        logger.info("\n" + tabulate(price_data, headers=price_headers) + "\n")

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
            open_trade_price = self.trading_session.trades[-1][5]

            return open_trade_price

        return None

    def is_trading_time(self, date_time) -> bool:

        logger.debug(f"Date time: {date_time}")

        day = date_time.weekday()
        hour = date_time.hour

        if day == 4 and hour >= 20:
            return False

        pause_from_dt = datetime.combine(date_time, datetime.strptime(self.pause_start, '%H:%M:%S').time())
        pause_to_dt = datetime.combine(date_time, datetime.strptime(self.pause_end, '%H:%M:%S').time())

        if pause_from_dt < date_time < pause_to_dt:
            return False

        return True

    def get_last_trade_time(self):

        date_time = None

        if len(self.trading_session.trades) > 0:
            date_time_s = self.trading_session.trades[-1][0]
            date_time = datetime.strptime(date_time_s, utils.date_format).replace(tzinfo=None)

        return date_time

