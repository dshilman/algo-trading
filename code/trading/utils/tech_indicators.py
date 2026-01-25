import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


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
def calculate_rsi(prices: pd.Series):

    period = prices.size
    delta = prices.diff()
    gain = delta.where(delta.gt(0), 0)
    loss = -delta.where(delta.lt(0), 0)

    avg_gain = gain.ewm(com=period , min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(com=period , min_periods=period).mean().iloc[-1]

    rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 4)

def compute_rsi(close: pd.Series) -> pd.Series:

    period = close.size
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_rsi_new(S):
    
    prices = pd.Series(S)
    delta = prices.diff()
    gain = delta.where(delta.gt(0), 0)
    loss = -delta.where(delta.lt(0), 0)

    avg_gain = gain.mean()
    avg_loss = loss.mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_ema(S: pd.Series, span=15):

   return S.ewm(span=span, adjust=False).mean().iloc[-1]

def calculate_slope(S: pd.Series) -> float:
    x = np.arange(len(S))
    return np.polyfit(x, np.asarray(S.values), 1)[0]

def predict_next(y):

    x = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression()
    model.fit(x, y.values.reshape(-1, 1))
    next_x = np.array([[len(y)]])
    next_pred = model.predict(next_x)[0, 0]

    return next_pred

def slope(y):

    x = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression()
    model.fit(x, y.values.reshape(-1, 1))

    return model.coef_[0][0]

def intercept(y):

    x = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression()
    model.fit(x, y.values.reshape(-1, 1))

    return model.intercept_

def compute_price_momentum(close: pd.Series) -> float:
    window = close.size
    open = close.shift()

    momemntum =  close.pct_change(window-1)
    strength = (close > open).astype(int).rolling(window=window, min_periods=window).sum() / window
    momemntum_strength = momemntum.iloc[-1] * strength.iloc[-1]

    return momemntum_strength