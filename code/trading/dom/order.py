class Order ():
    def __init__(self, instrument, price, trade_units, sl_price, trailing_sl, tp_price):
        super().__init__()
        self.instrument = instrument
        self.price = price
        self.units = trade_units
        self.sl = sl_price
        self.trailing_sl = trailing_sl
        self.tp = tp_price

    def __str__(self):
        return f"Order: instrument: {self.instrument}, units: {self.units}, price: {self.price}, stopp loss: {self.sl}, trailing_sl: {self.trailing_sl}, take profit: {self.tp}"

    def __repr__(self):
        return f"Order: instrument: {self.instrument}, units: {self.units}, price: {self.price}, stopp loss: {self.sl}, trailing_sl: {self.trailing_sl}, take profit: {self.tp}"
