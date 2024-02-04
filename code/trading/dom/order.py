import logging
import os
import sys
from pathlib import Path

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from dom.base import BaseClass

class Order (BaseClass):
    def __init__(self, instrument, price, trade_units, sl_dist, tp_price, logger = None):
        super().__init__(logger)
        self.instrument = instrument
        self.price = price
        self.units = trade_units
        self.sl = sl_dist
        self.tp = tp_price

    def __str__(self):
        return f"Order: instrument: {self.instrument}, units: {self.units}, price: {self.price}, stopp loss: {self.sl}, take profit: {self.tp}"

    def __repr__(self):
        return f"Order: instrument: {self.instrument}, units: {self.units}, price: {self.price}, stopp loss: {self.sl}, take profit: {self.tp}"
