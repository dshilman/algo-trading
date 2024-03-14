class PauseTradingException(Exception):
    
    def __init__(self, hours:int):
        self.hours = hours
        super().__init__(f"Pause trading for {self.hours} hour(s)")
