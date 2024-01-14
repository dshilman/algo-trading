import configparser
import logging
import sys

from trader import Order, Strategy, Trade_Action, Trader

logger = logging.getLogger("trader_oanda")

class BB_to_SMA_Strategy(Strategy):
    def __init__(self, instrument, pairs_file):
        super().__init__(instrument, pairs_file)


    def determine_action(self, bid, ask, units, units_to_trade) -> Trade_Action:
        
        price = round((bid + ask) / 2, 4)
        spread = round(ask - bid, 4)
        target = self.target
        instrument = self.instrument

        if units != 0:  # if already have positions
            logger.debug(f"Have {units} positions, checking if need to close")
            trade = self.check_if_need_close_trade(instrument, units, price, target, spread)
            if trade is not None:
                return trade

        # check if need to open a new position
        logger.debug(f"Have {units} positions, checking if need to open")
        trade = self.check_if_need_open_trade(instrument, units, price, target, spread, units_to_trade)
        if trade is not None:
            return trade

        return None

    def check_if_need_open_trade(self, instrument, units, price, target, spread, units_to_trade):
        
        signal = 0

        if spread >= (self.bb_upper - target):                            
            logger.warning (f"Current spread: {spread} is too large for price: {price} and target: {target}")
            return None
        
        
        if units == 0 or abs(units) <= 2 * units_to_trade:
            if price < self.bb_lower and self.rsi < 30 and self.rsi > self.rsi_min: # if price is below lower BB, BUY
                signal = 1
                logger.info(f"Go Long - BUY at price: {price}, rsi: {self.rsi}")
            elif price > self.bb_upper and self.rsi > 70 and self.rsi < self.rsi_max:  # if price is above upper BB, SELL
                signal = -1
                logger.info(f"Go Short - SELL at price: {price}, rsi: {self.rsi}")
        
        if signal != 0:
            return Trade_Action(instrument, signal * units_to_trade, price, target, spread)

        return None


    def check_if_need_close_trade(self, instrument, units, price, target, spread):

        signal = 0

        if units > 0:  # if already have long positions
            logger.debug(f"Have {units} positions, checking if need to close")
            if price > target and self.rsi < self.rsi_max:  # if price is above target SMA, SELL
                signal = -1
                logger.info(f"Close long position - Sell {units} units at price: {price}, sma: {target}, rsi: {self.rsi}")
        elif units < 0:  # if alredy have short positions
            if price < target and self.rsi > self.rsi_min:  # price is below target SMA, BUY
                signal = 1
                logger.info(f"Close short position  - Buy {units} units at price: {price}, sma: {target}, rsi: {self.rsi}")

        if signal != 0:
            return Trade_Action(instrument, signal * units, price, target, spread)

        return None




    def create_order(self, trade_action: Trade_Action, sl_perc, tp_perc, have_units) -> Order:
        
        order = None

        if sl_perc:
            if trade_action.spread / trade_action.price >= sl_perc:
                logger.warning(f"Current spread: {trade_action.spread} is too large for price: {trade_action.price} and sl_perc: {sl_perc}")
                return None
            sl_dist = round(trade_action.price * sl_perc, 4)

        else:
            sl_dist = None

        if tp_perc:
            tp_price = round(trade_action.price + (1 if trade_action.units > 0 else -1) * trade_action.price * tp_perc, 2)
        else:
            tp_price = None

        comment = None
        if have_units >= 0 and trade_action.units > 0:
            comment = "Going Long"
        elif have_units <= 0 and trade_action.units < 0:
            comment = "Going Short"
        elif have_units > 0 and trade_action.units < 0:
            comment = "Closing Long"
        elif have_units < 0 and trade_action.units > 0:
            comment = "Closing Short"

        order = Order(
            instrument = trade_action.instrument,
            price = trade_action.price,
            trade_units = trade_action.units,
            sl_dist = sl_dist,
            tp_price = str(tp_price),
            comment = comment
        )
        logger.debug(order)

        return order


class BB_Strategy_SMA_Target_Trader(Trader):
    def __init__(self, conf_file, pairs_file, instrument, unit_test = False):

        strategy = BB_to_SMA_Strategy(instrument, pairs_file)

        super().__init__(conf_file, pairs_file, strategy, unit_test)


if __name__ == "__main__":

    args = sys.argv[1:]

    pair = args[0]

    
    trader = BB_Strategy_SMA_Target_Trader(
        conf_file="oanda.cfg",
        pairs_file="pairs.ini",
        instrument=pair
    )
    trader.start_trading()

