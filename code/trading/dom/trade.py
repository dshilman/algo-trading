class Trade_Action():
    def __init__(self, instrument, units, price, open_trade = False, sl_trade = False):
        super().__init__()
        self.instrument = instrument
        self.units = units
        self.price = price
        self.open_trade = open_trade
        self.sl_trade = sl_trade
  

    def __str__(self):
        return f"Trade_Action: instrument: {self.instrument}, units: {self.units}, price: {self.price}" 

    def __repr__(self):
        return f"Trade_Action: instrument: {self.instrument}, units: {self.units}, price: {self.price}"       
