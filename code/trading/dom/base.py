import logging
import os
import sys
from pathlib import Path

# file = Path(__file__).resolve()
# parent, root = file.parent, file.parents[1]
# sys.path.append(str(root))

class BaseClass ():
    def __init__(self, logger: logging.Logger = None):
        super().__init__()
        self.logger = logger

        if self.logger == None:
            self.logger = logging.getLogger()
            self.logger.setLevel(logging.INFO)


    def log(self, message, level = logging.INFO):
        
        if not self.logger == None:
            self.logger.log(level, message)
        else:
            print(message)


    def log_warning(self, message):
        self.log(message, logging.WARNING)

    def log_debug(self, message):
        self.log(message, logging.DEBUG)

    def log_error(self, message):
        self.log(message, logging.ERROR)

    def log_exception(self, message):
        self.logger.exception(message)
        
    def log_info(self, message):
        self.log(message, logging.INFO)
