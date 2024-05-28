import numpy as np
import pandas as pd
# from scipy.stats import linregress


def calculate_slope(S: pd.Series):

    X = np.arange(len(S))
    Y = S.values

    return ((X*Y).mean() - X.mean()*Y.mean()) / ((X**2).mean() - (X.mean())**2)

    # slope, _, _, _, _ = linregress(X, Y)
    # return slope

def count_sma_crossover(S: pd.Series):

    count = 0
    prev_value = None

    for i in S:
        if prev_value is not None and i * prev_value < 0:
            count += 1
        elif prev_value is not None and i * prev_value == 0:
            continue
        
        prev_value = i

    return count

    
def calculate_momentum(S: pd.Series, n):

    return (S - S.shift(n)).mean()

# Calculate RSI
def calculate_rsi(prices: pd.Series, period=14):
    
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean().iloc[-1]

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 4)

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

def calculate_slope(S: pd.Series):

    x = np.arange(S.size)
    fit = np.polyfit(x, S.values, deg=1)
    slope = fit[0]
    return slope

def calculate_slope_ema(S: pd.Series, span=15):

   return S.ewm(span=span, adjust=False).mean()

