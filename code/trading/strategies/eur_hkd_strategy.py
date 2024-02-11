import logging

from api import OANDA_API
from strategy import TradingStrategy
from trading.api import OANDA_API
from trading.dom.order import Order
from trading.dom.trade import Trade_Action
from trading.dom.trading_session import Trading_Session
from trading.MyTT import RSI

logger = logging.getLogger()

class EUR_HKD_Strategy (TradingStrategy):

    def __init__(self, instrument, pair_file, api: OANDA_API = None, unit_test=False):
        super().__init__(instrument, pair_file, api, unit_test)

