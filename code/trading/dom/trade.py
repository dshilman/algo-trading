import pandas as pd


class Trade_Action():
    def __init__(self, time: pd.Timestamp, instrument, units, price: float, open_trade = False, sl_trade = False, tp_trade = False):
        super().__init__()
        self.time:pd.Timestamp = time
        self.instrument: str = instrument
        self.units: int = units
        self.price: float = price
        self.open_trade: bool = open_trade
        self.sl_trade: bool = sl_trade
        self.tp_trade: bool = tp_trade
  

    def __str__(self):
        return f'{"open new trade" if self.open_trade else "close trade"}, instrument: {self.instrument}, {"buy" if self.units > 0 else "sell"} units: {abs(self.units)}, price: {self.price}'

    def __repr__(self):
        return f'{"open new trade" if self.open_trade else "close trade"}, instrument: {self.instrument}, {"buy" if self.units > 0 else "sell"} units: {abs(self.units)}, price: {self.price}'
