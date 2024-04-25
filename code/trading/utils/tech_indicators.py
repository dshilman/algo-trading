import numpy as np
import pandas as pd
# from scipy.stats import linregress


def calculate_slope(S: pd.Series):

    X = np.arange(len(S))
    Y = S.values

    return ((X*Y).mean() - X.mean()*Y.mean()) / ((X**2).mean() - (X.mean())**2)

    # slope, _, _, _, _ = linregress(X, Y)
    # return slope

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

def calculate_rsi_new(S, period=14):
    
    prices = pd.Series(S)
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.mean()
    avg_loss = loss.mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi
