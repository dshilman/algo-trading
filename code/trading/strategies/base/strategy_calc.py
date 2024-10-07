from trading.utils.tech_indicators import (
    count_sma_crossover, calculate_rsi, calculate_slope, calculate_ema)
from trading.strategies.base.strategy_base import TradingStrategyBase
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

        self.print_indicators_count = 0

    def add_tickers(self, ticker_df: pd.DataFrame):

        # logger.debug(f"Adding tickers to dataframe: {ticker_df}")

        df = self.data.copy()
        df = pd.concat([df, ticker_df])
        df = df.reset_index().drop_duplicates(
            subset='time', keep='last').set_index('time')
        self.data = df.tail(self.SMA * 4)

        # logger.debug("After new tickers:\n" + df.iloc[-1:].to_string(header=True))

    def calc_indicators(self):

        df: pd.DataFrame = self.data.copy()

        instrument = self.instrument

        # DEV = self.DEV
        std_dev = 2
        period_long = 200
        period_short = 30

        # Volume Momentum
        df["volume_pct_change"] = df["volume"].pct_change()
        df["volume_max"] = df["volume"].rolling(period_short).max()

        df["price_std"] = df[instrument].rolling(period_long).std()
        # df["price_std_mean"] = df['price_std'].rolling(period_long).mean()

        # Bollinger Band
        df["sma_long"] = df[instrument].rolling(period_long).mean()
        df["bb_lower"] = df["sma_long"] - df["price_std"] * std_dev
        df["bb_upper"] = df["sma_long"] + df["price_std"] * std_dev

        # MACD
        df["ema_long"] = df[instrument].rolling(period_long).apply(lambda x: calculate_ema(S=x))
        # df['ema_long_slope'] = df["ema_long"].rolling(period_long).apply(lambda x: calculate_slope(x))

        df['ema_short'] = df[instrument].rolling(period_short).apply(lambda x: calculate_ema(S=x))
        # df['ema_short_slope'] = df["ema_short"].rolling(period_short).apply(lambda x: calculate_slope(x))

        # Momentum
        df[instrument + "_diff"] = df[instrument].diff()
        df["price_momentum_long"] = df[instrument + "_diff"].rolling(period_long).sum()
        df["price_momentum_long_min"] = df['price_momentum_long'].rolling(period_long).min()
        df["price_momentum_long_max"] = df['price_momentum_long'].rolling(period_long).max()

        df["price_momentum_short"] = df[instrument + "_diff"].rolling(period_short).sum()
        df["price_momentum_short_min"] = df["price_momentum_short"].rolling(period_short).min()
        df["price_momentum_short_max"] = df["price_momentum_short"].rolling(period_short).max()


        # RSI
        # df["rsi_long"] = df[instrument].rolling(period_long).apply(lambda x: calculate_rsi(x, period_long))
        # df["rsi_long_prev"] = df.rsi_long.shift()
        # df["rsi_long_max"] = df['rsi_long'].rolling(period_long).max()
        # df["rsi_long_min"] = df['rsi_long'].rolling(period_long).min()

        df["rsi_short"] = df[instrument].rolling(period_short).apply(lambda x: calculate_rsi(x, period_short))
        df["rsi_short_pct_change"] = df["rsi_short"].pct_change()
        df["rsi_short_max"] = df['rsi_short'].rolling(period_short).max()
        df["rsi_short_min"] = df['rsi_short'].rolling(period_short).min()

        # df["rsi_diff"] = df.rsi.diff()
        # df["rsi_momentum_" + str(period)] = df["rsi_diff"].rolling(period).sum()
        # df["rsi_momentum_" + str(period) + "_max"] = df["rsi_momentum_" + str(period)].rolling(period).max()
        # df["rsi_momentum_" + str(period) + "_min"] = df["rsi_momentum_" + str(period)].rolling(period).min()

        # df['rsi_ema'] = df["rsi"].rolling(period).apply(lambda x: calculate_ema(S = x, span = period))
        # df['rsi_ema_slope'] = df["rsi_ema"].rolling(period).apply(lambda x: calculate_slope(x))
        # df["rsi_ema_slope_max"] = df['rsi_ema_slope'].rolling(period).max()
        # df["rsi_ema_slope_min"] = df['rsi_ema_slope'].rolling(period).min()

        # df["price_max"] = df[instrument].rolling(period_long).max()
        # df["price_min"] = df[instrument].rolling(period_long).min()

        # df["greater_sma"] = df["sma_long"] - df[instrument]
        # df["greater_sma"] = df["greater_sma"].apply(
        #     lambda x: 1 if x > 0 else -1 if x < 0 else 0)
        # df["sma_crossover"] = df["greater_sma"].rolling(
        #     period_long).apply(lambda x: count_sma_crossover(x))

        # df.drop(columns=["greater_sma"], inplace=True)

        
        # if (not self.backtest and self.print_indicators_count % 60 == 0) or self.unit_test:
        #     logger.info("\n" + df.tail(10).to_string(header=True))

        # self.print_indicators_count = self.print_indicators_count + 1

        self.data = df

    def set_strategy_indicators(self, row: pd.Series = None, time=None):  # type: ignore

        trading_time = time
        if row is None:
            row = self.data.iloc[-1]
            trading_time = self.data.index[-1]

        logger.debug("Setting strategy indicators")

        self.ask = row["ask"]
        self.bid = row["bid"]
        self.price = row[self.instrument]
        # self.price_max = row["price_max"]
        # self.price_min = row["price_min"]
        self.price_std = row['price_std']

        # MACD
        # self.ema_long = row["ema_long"]
        self.ema_short = row['ema_short']

        # Bollinger Band
        self.sma_long = row['sma_long']
        self.bb_low = row['bb_lower']
        self.bb_high = row['bb_upper']

        # self.price_ema_long_slope = row["ema_long_slope"]
        self.price_ema_short = row["ema_short"]
        # self.price_ema_short_slope = row["ema_short_slope"]
        # self.price_ema_short_slope_max = row["ema_short_slope_max"]
        # self.price_ema_short_slope_min = row["ema_short_slope_min"]

        # Momentum
        self.price_momentum_long = row["price_momentum_long"]
        # self.price_momentum_long_mean = row["price_momentum_long_mean"]
        self.price_momentum_long_min = row["price_momentum_long_min"]
        self.price_momentum_long_max = row["price_momentum_long_max"]

        
        self.price_momentum_short = row["price_momentum_short"]
        self.price_momentum_short_min = row["price_momentum_short_min"]
        self.price_momentum_short_max = row["price_momentum_short_max"]
        
        # self.price_momentum_short_mean = row["price_momentum_short_mean"]
        

        # RSI
        # self.rsi_long = round(row["rsi_long"], 4)
        # self.rsi_long_prev = round(row["rsi_long_prev"], 4)
        # self.rsi_long_max = round(row["rsi_long_max"], 4)
        # self.rsi_long_min = round(row["rsi_long_min"], 4)

        self.rsi_short = round(row["rsi_short"], 4)
        self.rsi_short_pct_change = round(row["rsi_short_pct_change"], 4)
        self.rsi_short_max = round(row["rsi_short_max"], 4)
        self.rsi_short_min = round(row["rsi_short_min"], 4)

        
        # Volume Momentum
        # self.volume_momentum_short = row ["volume_momentum_short"]
        # self.volume_momentum_long = row ["volume_momentum_long"]
        self.volume = row ["volume"]
        self.volume_pct_change = row ["volume_pct_change"]
        self.volume_max = row ["volume_max"]


        if not self.backtest:
            self.print_indicators()

        self.is_trading = True
        if "status" in row:
            self.is_trading = row["status"] == "tradeable"

        if self.rsi_short == self.rsi_short_min:
            self.rsi_min_price = self.price
            self.rsi_min_time = trading_time
        elif self.rsi_short == self.rsi_short_max:
            self.rsi_max_price = self.price
            self.rsi_max_time = trading_time

    def print_indicators(self):

        logger.info("*********** PRICE *************")
        price_data = [[self.ask, self.bid, self.price,
                       self.price_min, self.price_max, self.price_std]]
        price_headers = ["ASK PRICE", "BID PRICE",
                         "MID PRICE", "PRICE MIN", "PRICE MAX", "PRICE STD"]
        logger.info("\n" + tabulate(price_data, headers=price_headers) + "\n")

        logger.info("*********** MACD and BOLLINGER *************")
        macd_bb_data = [[self.ema_short, self.ema_long, self.sma_long,
                         self.bb_low, self.bb_high, self.sma_crossover]]
        macd_bb_headers = ["EMA SHORT", "EMA LONG",
                           "SMA LONG", "BB_LOW", "BB_HIGH", "SMA CROSSOVER"]
        logger.info("\n" + tabulate(macd_bb_data,
                    headers=macd_bb_headers) + "\n")

        logger.info("*********** MOMENTUM *************")
        momentum_data = [[self.price_momentum_long, self.price_momentum_short]]
        momentum_headers = ["PRICE MOMENTUM LONG", "PRICE MOMENTUME SHORT"]
        logger.info("\n" + tabulate(momentum_data,
                    headers=momentum_headers) + "\n")

        logger.info("*********** RSI *************")
        rsi_data = [[self.rsi_long, self.rsi_long_min, self.rsi_long_max,
                     self.rsi_short, self.rsi_short_min, self.rsi_short_max]]
        rsi_headers = ["RSI LONG", "RSI LONG MIN", "RSI LONG MAX",
                       "RSI SHORT", "RSI SHORT MIN", "RSI SHORT MAX"]
        logger.info("\n" + tabulate(rsi_data, headers=rsi_headers) + "\n")

        logger.info("*********** VOLUME MOMENTUM *************")
        volume_momentume_data = [[self.volume_momentum_long, self.volume_momentum_short]]
        volume_momentume_headers = ["VOLUME MOMENTUM LONG", "VOLUME MOMENTUM SHORT"]
        logger.info("\n" + tabulate(volume_momentume_data, headers=volume_momentume_headers) + "\n")


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

        pause_from_dt = datetime.combine(
            date_time, datetime.strptime(self.pause_start, '%H:%M:%S').time())
        pause_to_dt = datetime.combine(
            date_time, datetime.strptime(self.pause_end, '%H:%M:%S').time())

        if pause_from_dt < date_time < pause_to_dt:
            return False

        return True

    def get_last_trade_time(self):

        date_time = None

        if len(self.trading_session.trades) > 0:
            date_time_s = self.trading_session.trades[-1][0]
            date_time = datetime.strptime(
                date_time_s, "%m/%d/%Y %H:%M:%S").replace(tzinfo=None)

        return date_time

    def get_trade_rsi(self):

        rsi = None

        if len(self.trading_session.trades) > 0:
            rsi = self.trading_session.trades[-1][6]

        return rsi

    def reverse_rsi_up(self, trading_time=None):
        pass

    def reverse_rsi_down(self, trading_time=None):
        pass

    def rsi_jump(self, jump=None):

        if jump is None:
            jump = self.rsi_change

        return self.rsi_max - self.rsi_min > jump \
            and self.rsi_min_time is not None and self.rsi_max_time is not None \
            and self.rsi_min_time < self.rsi_max_time

    def rsi_drop(self, drop=None):

        if drop is None:
            drop = self.rsi_change

        return self.rsi_max - self.rsi_min > drop \
            and self.rsi_min_time is not None and self.rsi_max_time is not None \
            and self.rsi_min_time > self.rsi_max_time
