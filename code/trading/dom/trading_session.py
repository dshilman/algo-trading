import logging
from datetime import datetime, timedelta, timezone
from tabulate import tabulate

from pathlib import Path
import sys
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from dom.trade import Trade_Action


logger = logging.getLogger()
class Trading_Session():

    def __init__(self):
        
        self.trades = []
        self.pl:float = 0
        self.go_short = 0
        self.go_long = 0
        self.close_short = 0
        self.close_long = 0
        self.outstanding = 0
        self.trade_cost = 0
        self.trade_pl = 0
        self.have_units = 0

        super().__init__()



    def add_trade(self, trade_action: Trade_Action, have_units: int, date_time=None):

        if date_time is None:
            date_time = datetime.utcnow()

        transaction = None
        if have_units == 0 and trade_action.units > 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.outstanding = self.trade_cost
            self.trade_pl = 0
            self.go_long = self.go_long + 1
            transaction = "Go Long"
            # logger.info(f"Go Long -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
        elif have_units == 0 and trade_action.units < 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.outstanding = self.trade_cost
            self.trade_pl = 0
            self.go_short = self.go_short + 1
            transaction = "Go Short"
            # logger.info(f"Go Short -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
        elif have_units > 0 and trade_action.units < 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.trade_pl = self.trade_cost - self.outstanding
            self.pl = self.pl + self.trade_pl
            self.close_long = self.close_long + 1
            transaction = "Close Long"
            # logger.info(f"Close Long -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
        elif have_units < 0 and trade_action.units > 0:
            self.trade_cost = abs(trade_action.units) * trade_action.price
            self.trade_pl = self.outstanding - self.trade_cost
            self.pl = self.pl + self.trade_pl
            self.close_short = self.close_short + 1
            transaction = "Close Short"
            # logger.info(f"Close Short -- shares: {trade_action.units}, at price: {trade_action.price}, P&L {'${:,.2f}'.format(self.pl)}")
        
        self.have_units = self.have_units + trade_action.units
        self.trades.append([date_time.strftime("%m/%d/%Y %H:%M:%S"), trade_action.transaction, trade_action.units, trade_action.price, '${:,.2f}'.format(self.trade_cost), '${:,.2f}'.format(self.trade_pl), self.have_units, '${:,.2f}'.format(self.pl)])

        return self.have_units

    def print_trades(self):

        logger.info("\n" + 100 * "-")        
        columns = ["datetime", "transaction", "trade units", "price", "trade cost", "trade p&l", "have units", "total p&l"]
        logger.info("\n" + tabulate(self.trades, headers = columns))
        logger.info(f"Finished Trading Session with P&L: {'${:,.2f}'.format(self.pl)}, # of trades: {len(self.trades)}, have units: {self.have_units}")
        logger.info(f"go long: {self.go_long}, go short: {self.go_short}, close long: {self.close_long}, close short: {self.close_short}")
        logger.info("\n" + 100 * "-")
