class Trade_Action():
    def __init__(self, instrument, units, price, spread, transaction, open_trade = False, sl_trade = False, strategy = None):
        super().__init__()
        self.instrument = instrument
        self.units = units
        self.price = price
        self.spread = spread
        self.transaction = transaction
        self.open_trade = open_trade
        self.sl_trade = sl_trade
        self.strategy = strategy
        # self.target = price + signal * spread


    def __str__(self):
        return f"Trade_Action: instrument: {self.instrument}, units: {self.units}, price: {self.price}, spread: {self.spread}, transaction: {self.transaction}" 

    def __repr__(self):
        return f"Trade_Action: instrument: {self.instrument}, units: {self.units}, price: {self.price}, spread: {self.spread}, transaction: {self.transaction}"       
