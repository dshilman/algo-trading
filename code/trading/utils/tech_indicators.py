import numpy as np
import pandas as pd


def calculate_slope(S):
    M = pd.Series(S)
    poly = np.polyfit(M.index, M.values, deg=1)
    return poly[0]

def calculate_momentum(S: pd.Series, n):

    return (S - S.shift(n)).mean()

# Calculate RSI
def calculate_rsi(S, period=14):
    
    prices = pd.Series(S)
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean().iloc[-1]

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi
