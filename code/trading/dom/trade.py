from dom.base import BaseClass

class Trade_Action(BaseClass):
    def __init__(self, instrument, units, price, spread, open_trade = False, logger = None):
        super().__init__()
        self.instrument = instrument
        self.units = units
        self.price = price
        self.spread = spread
        self.open_trade = open_trade


    def __str__(self):
        return f"Trade_Action: instrument: {self.instrument}, units: {self.units}, price: {self.price}, spread: {self.spread}" 

    def __repr__(self):
        return f"Trade_Action: instrument: {self.instrument}, units: {self.units}, price: {self.price}, spread: {self.spread}"       
