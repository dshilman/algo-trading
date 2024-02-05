import configparser
import json

import pandas as pd
from tabulate import tabulate
from trading.MyTT import RSI

from trading.dom.base import BaseClass
from trading.dom.order import Order
from trading.dom.trade import Trade_Action
from trading.dom.trading_session import Trading_Session


class TradingStrategy(BaseClass):
    def __init__(self, instrument, pair_file, logger = None, unit_test = False):
        super().__init__(logger)

        self.trading_session = Trading_Session(logger)

        self.instrument = instrument
        
        self.unit_test = unit_test
        config = configparser.ConfigParser()  
        config.read(pair_file)
        self.sma_value = int(config.get(instrument, 'SMA'))
        self.dev = float(config.get(instrument, 'dev'))
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        self.sl_perc = float(config.get(self.instrument, 'sl_perc'))
        self.tp_perc = float(config.get(self.instrument, 'tp_perc'))


        self.data = None
        # Caculated attributes
        self.bb_upper =  None
        self.bb_lower =  None
        self.sma = None
        self.rsi = None
        self.momentum = None
        self.momentum_long = None

        self.momentum_prev = None
        self.momentum_min = None


    def execute_strategy(self, have_units, resampled_tick_data: pd.DataFrame = None):

        self.calc_indicators(resampled_tick_data)

        trade_action = self.determine_trade_action(have_units)
        if trade_action is not None:
            # self.log_info(f"trade_action: {trade_action}")
            order = self.create_order(trade_action, self.sl_perc, self.tp_perc, self.units)

            if order is not None:
                have_units = self.submit_order(order, have_units)

        return have_units

    def calc_indicators(self, resampled_tick_data: pd.DataFrame = None):
        
        df = self.data.copy()
        
        if resampled_tick_data is not None and resampled_tick_data.size > 0:
            df = pd.concat([df, resampled_tick_data])
      
        df = df.tail(self.sma_value * 2)
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

                
        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.sma_value).mean()
        std = df[self.instrument].rolling(self.sma_value).std() * self.dev
        
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std
        df["RSI"] = df[self.instrument][-self.sma_value:].rolling(29).apply(lambda x: RSI(x.dropna().values, N=28))
        # df["RSI_EMA"] = df.RSI[-self.sma_value:].ewm(span=10, adjust=False, ignore_na = True).mean()
        # df["rsi_ema_slope"] = df["RSI_EMA"][-self.sma_value:].rolling(10).apply(lambda x: MyTT.SLOPE(x.dropna().values, 10))
        # df["ema"] = df[self.instrument][-self.sma_value:].ewm(span=10, adjust=False, ignore_na = True).mean()
 
        self.rsi = df.RSI.iloc[-1]
        self.rsi_max = df ['RSI'][-10:].max()
        self.rsi_min = df ['RSI'][-10:].min()
        self.rsi_hist = df ['RSI'][-8:].values
       
        df ["momentum"] = df[self.instrument][-self.sma_value:].rolling(8).apply(lambda x: (x.iloc[0] - x.iloc[-1]) / x.iloc[0])
        self.momentum = df.momentum.iloc[-1]
        self.momentum_prev = df.momentum.iloc[-2]

        self.price = round(df[self.instrument].iloc[-1], 6)
        self.price_max = round(df [self.instrument][-10:].max(), 6)
        self.price_min = round(df [self.instrument][-10:].min(), 6)

        self.ask = round(df.ask.iloc[-1], 6)
        self.bid = round(df.bid.iloc[-1], 6)

        self.bb_lower = round(df.Lower.iloc[-1], 6)
        self.bb_upper =  round(df.Upper.iloc[-1], 6)
        self.sma = round(df.SMA.iloc[-1], 6)

        self.log_debug (df)
    
        self.print_indicators()
        
        self.data = df.copy()

    
    def submit_order(self, order: Order, units: int):

        self.log_info(f"Submitting Order: {order}")
        if not self.unit_test:        
            oanda_order = self.create_order(instrument = order.instrument, units = order.units, sl_distance = order.sl, tp_price=order.tp, suppress=True, ret=True)
            self.report_trade(oanda_order)
            if "rejectReason" not in oanda_order:
                units = units + order.units
                self.log_info(f"New # of {order.instrument} units: {self.units}")
            else:
                error = f"Order was not filled: {oanda_order ['type']}, reason: {oanda_order['rejectReason']}"
                self.log_error(error)
                raise Exception(error)
        else:
            units = units + order.units
            self.log_info(f"New # of {order.instrument} units: {self.units}")

        return units

    def report_trade(self, order):

        self.log_info("\n" + 100 * "-" + "\n")
        self.log_info()
        self.log_info("\n" + self.strategy.data[-10:].to_string(header=True))
        self.log_info()
        self.print_indicators(order.get("price"))
        self.log_info()
        self.log_info(json.dumps(order, indent = 2))
        self.log_info("\n" + 100 * "-" + "\n")

    def determine_trade_action(self, have_units) -> Trade_Action:

        if have_units != 0:  # if already have positions
            self.log_debug(f"Have {have_units} positions, checking if need to close")
            trade = self.check_if_need_close_trade(have_units)
            if trade is not None:
                return trade
                
        self.log_debug(f"Have {have_units} positions, checking if need to open")
        trade = self.check_if_need_open_trade(have_units)
        if trade is not None:
            return trade

        return None


    def check_if_need_open_trade(self, have_units):
        
        spread = round(self.ask - self.bid, 4)
        # check if need to open a new position
        if spread >= abs(self.bb_upper - self.sma):                            
            self.log_info(f"Current spread: {spread} is too large to trade for possible gain: {round(abs(self.bb_upper - self.sma), 6)}")
            return None

        # if abs(have_units) <= units_to_trade:
        if have_units == 0:
            
            signal = 0

            if self.ask < self.bb_lower and self.rsi_min < 30 and self.rsi_min in self.rsi_hist and self.momentum * self.momentum_prev <= 0: # if price is below lower BB, BUY
                signal = 1
                self.log_info(f"Go Long - BUY at ask price: {self.ask}, rsi: {self.rsi}")
            elif self.bid > self.bb_upper and self.rsi_max > 70 and self.rsi_max is self.rsi_hist and self.momentum * self.momentum_prev <= 0:  # if price is above upper BB, SELL
                signal = -1
                self.log_info(f"Go Short - SELL at bid price: {self.bid}, rsi: {self.rsi}")
            
            """
                Trade 1: +1,000 EUR/USD +SL @ 1.05
                Trade 2: +1,000 EUR/USD +SL @ 1.05 
                Trade 2 is cancelled because all trades with a SL, TP, or TS must have a unique size
            """
            if signal != 0:
                return Trade_Action(self.instrument, signal * (self.units_to_trade + (0 if have_units == 0 else 1)), (self.ask if signal > 0 else self.bid), spread, True)
                

        return None


    def check_if_need_close_trade(self, have_units):

        signal = 0
        spread = round(self.ask - self.bid, 4)

        if have_units > 0:  # if already have long positions
            if self.bid > self.sma and self.momentum * self.momentum_prev <= 0:  # price is above target SMA, SELL
                signal = -1
                self.log_info(f"Close long position - Sell {have_units} units at bid price: {self.bid}, sma: {self.sma}, rsi: {self.rsi}")
        elif have_units < 0:  # if alredy have short positions
            if self.ask < self.sma and self.momentum * self.momentum_prev <= 0:  # price is below target SMA, BUY
                signal = 1
                self.log_info(f"Close short position  - Buy {have_units} units at ask price: {self.ask}, sma: {self.sma}, rsi: {self.rsi}")

        """
            Negative sign if front of have_units "-have_units" means close the existing position
        """
        if signal != 0:
            return Trade_Action(self.instrument, -have_units, (self.ask if signal > 0 else self.bid), spread, False)

        return None

    def print_indicators(self):

        indicators = [[self.price, self.price_min, self.price_max, self.sma, self.bb_lower, self.bb_upper, self.rsi, self.rsi_min, self.rsi_max, self.momentum, self.momentum_prev]]
        columns=["PRICE", "PRICE MIN", "PRICE MAX", "SMA", "BB_LOW", "BB_HIGH", "RSI", "RSI MIN", "RSI MAX", "MOMENTUM", "MOMENTUM PREV"]
        self.log_info("\n" + tabulate(indicators, headers = columns))


    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units) -> Order:
        
        sl_dist = None
        tp_price = None

        # if trade_action.open_trade:
        if sl_perc:
            if trade_action.spread / trade_action.price >= sl_perc:
                self.log_warning(f"Current spread: {trade_action.spread} is too large for price: {trade_action.price} and sl_perc: {sl_perc}")
                return None
            """
                Have been getting STOP_LOSS_ON_FILL_DISTANCE_PRECISION_EXCEEDED when trading GBP_JPY
                I assume that the price is too high for 4 digit decimals, thus adding a rule
                if the price is grater that $100, do not use decimals for stop loss
            """
            sl_dist = round(trade_action.price * sl_perc, (4 if trade_action.price < 100 else 0))

            
        if tp_perc:
            tp_price = str(round(trade_action.price + (1 if trade_action.units > 0 else -1) * trade_action.price * tp_perc, (4 if trade_action.price < 100 else 0)))

        self.trading_session.add_trade(trade_action, have_units)

        order = Order(
            instrument = trade_action.instrument,
            price = trade_action.price,
            trade_units = trade_action.units,
            sl_dist = sl_dist,
            tp_price = tp_price
        )
        self.log_debug(order)

        return order    
