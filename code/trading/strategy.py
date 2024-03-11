import configparser
import json
import logging
import sys
from datetime import datetime, time
from pathlib import Path
from random import randint

import pandas as pd
from tabulate import tabulate

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from trading.api.oanda_api import OandaApi
from trading.dom.order import Order
from trading.dom.trade import Trade_Action
from trading.dom.trading_session import Trading_Session
from trading.errors import PauseTradingException
from trading.tech_indicators import (calculate_momentum, calculate_rsi,
                                     calculate_slope)

logger = logging.getLogger()

"""
Go Long (buy) when the ask price is below the low Bollinger Band and close trade (sell) when the bid price above the SMA

Go Short (sell) when the bid price is above the high Bollinger Band and close trade (buy) when the ask price below the low Bollinger Band

"""
class TradingStrategy():
    def __init__(self, instrument, pair_file, api = None, unit_test = False):
        super().__init__()

        self.trading_session = Trading_Session()

        self.instrument = instrument
        self.api:OandaApi = api
        self.unit_test = unit_test
        config = configparser.ConfigParser()  
        config.read(pair_file)
        self.sma_value = int(config.get(instrument, 'SMA'))
        self.dev = float(config.get(instrument, 'dev'))
        self.units_to_trade = int(config.get(instrument, 'units_to_trade'))
        self.sl_perc = float(config.get(self.instrument, 'sl_perc'))
        self.tp_perc = float(config.get(self.instrument, 'tp_perc'))
        self.low_rsi = float(config.get(self.instrument, 'low_rsi'))
        self.high_rsi = float(config.get(self.instrument, 'high_rsi'))
        self.pause_start = config.get(self.instrument, 'pause_start')
        self.pause_end = config.get(self.instrument, 'pause_end')
        self.target = float(config.get(self.instrument, 'target'))
        

        self.data = None
        # Caculated attributes
        self.bb_upper =  None
        self.bb_lower =  None
        self.sma = None

        self.price = None
        self.price_max = None
        self.price_min = None
        self.price_momentum = None
        self.price_momentum_prev = None
        self.price_target = None
        
        self.rsi = None
        self.rsi_min = None
        self.rsi_max = None
        self.rsi_avg = None
        self.rsi_momentum = None
        self.rsi_momentum_prev = None


    def execute_strategy(self):

        trading_time = datetime.utcnow()
        trade_action = self.determine_trade_action(trading_time)        

        if trade_action is not None:
            # logger.info(f"trade_action: {trade_action}")
            
            order = self.create_order(trade_action, self.sl_perc, self.tp_perc)

            if order is not None:
                self.submit_order(order)
                self.trading_session.add_trade(trade_action=trade_action, rsi=self.rsi)


        if trade_action is not None and trade_action.sl_trade:
            raise PauseTradingException(2)

        return

    def calc_indicators(self, resampled_tick_data: pd.DataFrame = None):
        
        df = self.data.copy()
        
        if resampled_tick_data is not None and resampled_tick_data.size > 0:
            df = pd.concat([df, resampled_tick_data])
      
        df = df.tail(self.sma_value * 3)
        df = df.reset_index().drop_duplicates(subset='time', keep='last').set_index('time')

                
        # ******************** define your strategy here ************************
        df["SMA"] = df[self.instrument].rolling(self.sma_value).mean()

        std = df[self.instrument].rolling(self.sma_value).std() * self.dev
        df["Lower"] = df["SMA"] - std
        df["Upper"] = df["SMA"] + std

        rsi_periods = int(self.sma_value/2)
        df["RSI"] = df[self.instrument][-self.sma_value:].rolling(rsi_periods).apply(lambda x: calculate_rsi(x.values, rsi_periods))

        df ["momentum"] = df[self.instrument][-self.sma_value:].rolling(8).apply(lambda x: calculate_momentum(x.iloc[0], x.iloc[-1]))

        df ["rsi_momentum"] = df.RSI[-self.sma_value:].rolling(8).apply(lambda x: calculate_momentum(x.iloc[0], x.iloc[-1]))
  
        self.ask = round(df.ask.iloc[-1], 6)
        self.bid = round(df.bid.iloc[-1], 6)
        self.sma = round(df.SMA.iloc[-1], 6)
        
        self.bb_lower = round(df.Lower.iloc[-1], 6)
        self.bb_upper =  round(df.Upper.iloc[-1], 6)

        period = 8

        last_rsi = df.RSI[-period:]
        self.rsi = round(last_rsi.iloc[-1], 4)
        self.rsi_min = round(last_rsi.min(), 4)
        self.rsi_max = round(last_rsi.max(), 4)
        self.rsi_avg = round(last_rsi.ewm(com=period - 1, min_periods=period).mean().iloc[-1], 4)

        self.rsi_momentum = round(df ["rsi_momentum"].iloc[-1], 6)
        self.rsi_momentum_prev = round(df ["rsi_momentum"].iloc[-2], 6)

        last_momentum = df.momentum[-period:].values
        self.price_momentum = round(last_momentum[-1], 6)
        self.price_momentum_prev = round(last_momentum[-2], 6)
        last_prices = df[self.instrument][-period:].values
        self.price = round(last_prices[-1], 6)
        self.price_min = round(last_prices[-period:].min(), 6)
        self.price_max = round(last_prices.max(), 6)
        self.price_target = round(self.get_target_price(), 6)

        logger.debug("\n" + df[-period:].to_string(header=True))
  
        self.print_indicators()
        
        self.data = df.copy()

    
    def submit_order(self, order: Order):

        logger.info(f"Submitting Order: {order}")
        if not self.unit_test:        
            # result = self.api.create_order(order=order)
            result = self.api.place_order(order=order)
            self.report_trade(result)
            if "rejectReason" in result:               
                error = f"Order was not filled: {result ['type']}, reason: {result['rejectReason']}"
                logger.error(error)
                raise Exception(error)
        
        return

    def report_trade(self, order):

        logger.info("\n" + 100 * "-" + "\n")
        logger.info("")
        logger.info("\n" + self.data[-8:].to_string(header=True))
        logger.info("")
        self.print_indicators()
        logger.info("")
        logger.info(json.dumps(order, indent = 2))
        logger.info("\n" + 100 * "-" + "\n")

    def determine_trade_action(self, trading_time) -> Trade_Action:

        have_units = self.trading_session.have_units

        if have_units != 0:  # if already have positions
            logger.debug(f"Have {have_units} positions, checking for stop loss")
            trade_action = self.check_for_sl(trading_time)
            if trade_action is not None:
                return trade_action

            logger.debug(f"Have {have_units} positions, checking if need to close")
            trade = self.check_if_need_close_trade()
    
            if trade is not None:
                return trade

        else:        
            logger.debug(f"Have {have_units} positions, checking if need to open")
            trade = self.check_if_need_open_trade(trading_time)
            if trade is not None:
                return trade

        return None


    def check_if_need_open_trade(self, trading_time):
        
        spread = round(self.ask - self.bid, 4)
        # check if need to open a new position
        # if 1.5 * spread >= abs(self.bb_upper - self.sma):                            
        #     logger.debug(f"Current spread: {spread} is too large to trade for possible gain: {round(abs(self.bb_upper - self.sma), 6)}")
        #     return None

        if self.ask < self.bb_lower and self.has_low_rsi(trading_time) and self.reverse_rsi_momentum(): # if price is below lower BB, BUY
        # if self.ask <= self.bb_lower and self.has_low_rsi() and self.price_momentum * self.price_momentum_prev <= 0: # if price is below lower BB, BUY
            signal = 1
            logger.info(f"Go Long - BUY at ask price: {self.ask}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, signal * (self.units_to_trade + randint(0, 5)), self.ask, spread, "Go Long - Buy", True, False)

        elif self.bid > self.bb_upper and self.has_high_rsi(trading_time) and self.reverse_rsi_momentum():  # if price is above upper BB, SELL
        # elif self.bid >= self.bb_upper and self.has_high_rsi() and self.price_momentum * self.price_momentum_prev <= 0:
            signal = -1
            logger.info(f"Go Short - SELL at bid price: {self.bid}, rsi: {self.rsi}")
            return Trade_Action(self.instrument, signal * (self.units_to_trade + randint(0, 5)), self.bid, spread, "Go Short - Sell", True, False)
            
        return
    

    def reverse_rsi_momentum(self):
        # do not change this logic
        if self.rsi_momentum > 0:
            return  self.rsi < self.rsi_max
        elif self.rsi_momentum < 0:
            return self.rsi_min < self.rsi
        else:
            return False

        # return self.rsi < self.rsi_max if self.rsi_momentum < 0 else self.rsi > self.rsi_min
        

    def reverse_price_momentum(self):
        # do not change this logic
        if self.price_momentum > 0:
            return self.price < self.price_max
        elif self.price_momentum < 0:
            return self.price > self.price_min
        else:
            return False
        # return self.price < self.price_max if self.price_momentum < 0 else self.price > self.price_min
        
    def has_high_rsi(self, trading_time):

        if self.risk_time(trading_time) or self.rsi_max - self.rsi >= 10:
            return self.rsi > 70
        else:
            return self.rsi_max > self.high_rsi
        
        # return self.rsi_max > (self.high_rsi if not self.risk_time(trading_time) else 70)
    
    def has_low_rsi(self, trading_time):
        
        if self.risk_time(trading_time) or self.rsi_max - self.rsi >= 10:
            return self.rsi < 30
        else:
            return self.rsi_min < self.low_rsi
        # return self.rsi_min < (self.low_rsi if not self.risk_time(trading_time) else 30)
    
    def get_target_price(self):

        target = None
        have_units = self.trading_session.have_units

        if have_units != 0 and len (self.trading_session.trades) > 0:
            transaction_price =  self.trading_session.trades[-1][3]
            # traded_units = self.trading_session.trades[-1][2]

            if have_units > 0: # long position
                target = min(self.sma,  transaction_price + self.target * (self.ask - self.bid))
       
            elif have_units < 0: # short position
                target = max(self.sma,  transaction_price - self.target * (self.ask - self.bid))
        else:
            target = self.sma

        return target

    
    def check_if_need_close_trade(self):

        have_units = self.trading_session.have_units
        
        if have_units > 0: # long position
            if self.bid > self.price_target and self.reverse_rsi_momentum():
                logger.info(f"Close long position - Sell {-have_units} units at bid price: {self.bid}, target: {self.price_target}")
                return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Long - Sell", False, False)

        if have_units < 0: # short position
            if self.ask < self.price_target and self.reverse_rsi_momentum():
                logger.info(f"Close short position  - Buy {-have_units} units at ask price: {self.ask}, target: {self.price_target}")
                return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Short - Buy", False, False)

        return None

    def check_for_sl(self, trading_time):

        have_units = self.trading_session.have_units

        if len (self.trading_session.trades) == 0:
            return None

        transaction_price =  self.trading_session.trades[-1][3]
        traded_units = self.trading_session.trades[-1][2]

        if (traded_units == have_units):
            if have_units < 0:
                current_loss_perc = round((self.ask - transaction_price)/transaction_price, 4)
                if current_loss_perc >= (self.sl_perc/2 if self.risk_time(trading_time) else self.sl_perc  - .0005):
                    logger.info(f"Close short position, - Stop Loss Buy, short price {transaction_price}, current ask price: {self.ask}, loss: {current_loss_perc}")
                    return Trade_Action(self.instrument, -have_units, self.ask, (self.ask - self.bid), "Close Short - Stop Loss Buy", False, True)

            if have_units > 0:
                current_loss_perc = round((transaction_price - self.bid)/transaction_price, 4)
                if current_loss_perc >= (self.sl_perc/2 if self.risk_time(trading_time) else self.sl_perc  - .0005):
                    logger.info(f"Close long position, - Stop Loss Sell, long price {transaction_price}, current bid price: {self.bid}, lost: {current_loss_perc}")
                    return Trade_Action(self.instrument, -have_units, self.bid, (self.ask - self.bid), "Close Long - Stop Loss Sell", False, True)
        
        return None

    def print_indicators(self):

        indicators = [[self.ask, self.bid, self.sma, self.bb_lower, self.bb_upper, self.rsi, self.rsi_min, self.rsi_max, '{0:f}'.format(self.rsi_momentum), '{0:f}'.format(self.price), '{0:f}'.format(self.price_min), '{0:f}'.format(self.price_max), '{0:f}'.format(self.price_momentum), '{0:f}'.format(self.price_target)]]
        columns=["ASK PRICE", "BID PRICE", "SMA", "BB_LOW", "BB_HIGH", "RSI", "RSI MIN", "RSI MAX", "RSI MOMENTUM", "PRICE", "PRICE MIN", "PRICE MAX", "PRICE MOMENTUM", "TARGET PRICE"]
        logger.info("\n" + tabulate(indicators, headers = columns) + "\n")


    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc) -> Order:
        
        tp_price = None
        sl_price = None

        # if trade_action.open_trade:
        if trade_action.spread / trade_action.price >= sl_perc:
            logger.warning(f"Current spread: {trade_action.spread} is too large for price: {trade_action.price} and sl_perc: {sl_perc}")
            return None
        if trade_action.open_trade:
            
            """
                Have been getting STOP_LOSS_ON_FILL_DISTANCE_PRECISION_EXCEEDED when trading GBP_JPY
                I assume that the price is too high for 4 digit decimals, thus adding a rule
                if the price is grater that $100, do not use decimals for stop loss
            """

            # sl_dist = round(trade_action.price * (sl_perc), (4 if trade_action.price < 100 else 0))
            sl_price = round(trade_action.price - (1 if trade_action.units > 0 else -1) * trade_action.price * sl_perc, (4 if trade_action.price < 100 else 0))

                
            if tp_perc:
                tp_price = round(trade_action.price + (1 if trade_action.units > 0 else -1) * trade_action.price * tp_perc, (4 if trade_action.price < 100 else 0))


        order = Order(
            instrument = trade_action.instrument,
            price = trade_action.price,
            trade_units = trade_action.units,
            # sl_dist = sl_dist,
            sl_price = sl_price,
            tp_price = tp_price
        )
        logger.debug(order)

        return order

    def risk_time(self, date_time) -> bool:

        logger.debug(f"Date time: {date_time}")

        pause_from_dt = datetime.combine(date_time, datetime.strptime(self.pause_start, '%H:%M:%S').time())
        pause_to_dt = datetime.combine(date_time, datetime.strptime(self.pause_end, '%H:%M:%S').time())


        if pause_from_dt < date_time < pause_to_dt:
            return True

        return False

    """
        SMA=200
        dev=2
        sl_perc=0.0025
        high_rsi=60
        low_rsi=35
        target=3
    """
    def __str__(self):
        return f"Strategy -- SMA: {self.sma_value}, STD: {self.dev}, stop loss: {self.sl_perc}, rsi high: {self.high_rsi}, rsi low: {self.low_rsi}, target: {self.target}"

    def __repr__(self):
        return f"Strategy -- SMA: {self.sma_value}, STD: {self.dev}, stop loss: {self.sl_perc}, rsi high: {self.high_rsi}, rsi low: {self.low_rsi}, target: {self.target}"
