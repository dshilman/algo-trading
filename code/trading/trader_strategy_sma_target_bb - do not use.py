import configparser
import logging
import sys

from trading.trader import Order, Strategy, Trade_Action, Trader

logger = logging.getLogger("trader_oanda")

class SMA_to_BB_Strategy(Strategy):
    def __init__(self, instrument, pairs_file):
        super().__init__(instrument, pairs_file)


    def check_if_need_open_trade(self, instrument, have_units, price, spread, units_to_trade):
        
        
        # if abs(have_units) <= units_to_trade:
        if have_units == 0:
            
            signal = 0

            if price > self.sma and price < self.bb_upper and self.rsi > 70 and self.rsi >= self.rsi_max: # if price is below lower BB, BUY
                signal = 1
                logger.info(f"Go Long - BUY at price: {price}, rsi: {self.rsi}")
            elif price < self.sma and self.rsi < 30 and self.rsi <= self.rsi_min and price > self.bb_lower:  # if price is above upper BB, SELL
                signal = -1
                logger.info(f"Go Short - SELL at price: {price}, rsi: {self.rsi}")
            
            """
                Trade 1: +1,000 EUR/USD +SL @ 1.05
                Trade 2: +1,000 EUR/USD +SL @ 1.05
                Trade 2 is cancelled because all trades with a SL, TP, or TS must have a unique size
            """
            if signal != 0:
                return Trade_Action(instrument, signal * (units_to_trade + (0 if have_units == 0 else 1)), price, spread, True)
                

        return None


    def check_if_need_close_trade(self, instrument, have_units, price, spread):

        signal = 0

        if have_units > 0:  # if already have long positions
            if price > self.bb_upper and self.rsi < self.rsi_max and price < self.price_max:  # if price is above target SMA, SELL
                signal = -1
                logger.info(f"Close long position - Sell {have_units} units at price: {price}, bb.upper: {self.bb_upper}, rsi: {self.rsi}")
        elif have_units < 0:  # if alredy have short positions
            if price < self.bb_lower and self.rsi > self.rsi_min and price > self.price_min:  # price is below target SMA, BUY
                signal = 1
                logger.info(f"Close short position  - Buy {have_units} units at price: {price}, bb.lower: {self.bb_lower}, rsi: {self.rsi}")

        """
            Negative sign if front of have_units "-have_units" means close the existing position
        """
        if signal != 0:
            return Trade_Action(instrument, -have_units, price, spread, False)

        return None


class SM_Strategy_BB_Target_Trader(Trader):
    def __init__(self, conf_file, pairs_file, instrument, unit_test = False):

        strategy = SMA_to_BB_Strategy(instrument, pairs_file)

        super().__init__(conf_file, pairs_file, strategy, unit_test)


if __name__ == "__main__":

    args = sys.argv[1:]

    pair = args[0]

    
    trader = SM_Strategy_BB_Target_Trader(
        conf_file="../data/oanda.cfg",
        pairs_file="../data/pairs.ini",
        instrument=pair
    )
    trader.start_trading()
