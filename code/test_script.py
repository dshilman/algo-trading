import pandas as pd

# Sample DataFrame
data = {
    "price": [101, 102, 100, 99, 103, 105, 98, 97, 106, 107, 109, 110, 134, 156, 167, 200, 145, 165, 198, 88, 66, 201, 202, 77, 204, 100],
    "ask": [101, 102, 100, 99, 103, 105, 98, 97, 106, 107, 109, 110, 134, 156, 167, 198, 145, 165, 198, 88, 66, 201, 202, 203, 204, 100],
    "bid": [101, 102, 100, 99, 103, 105, 98, 97, 106, 107, 109, 110, 134, 156, 167, 198, 145, 165, 198, 88, 66, 201, 202, 203, 204, 100]
}
index = pd.date_range(start="2024-02-12 09:00:00", periods=len(data["price"]), freq="min")  # 1-minute intervals
df = pd.DataFrame(data, index=index)
print(df)


# Resample by 5-minute intervals and compute high and low prices
# resampled_df["high"] = df["price"].rolling(5).resample("5min").aggregate({"price": ["max", "min", "last"], "ask": "last", "bid": "last"})

df["high"] = df["price"].rolling(5).max()
df["low"] = df["price"].rolling(5).min()
df["close"] = df["price"].rolling(5).apply(lambda x: x.iloc[-1])
df["ask"] = df["ask"].rolling(5).apply(lambda x: x.iloc[-1])
df["bid"] = df["bid"].rolling(5).apply(lambda x: x.iloc[-1])

resampled_df = df.resample("5min").last()


# Rename columns for clarity
# resampled_df.columns = ["high", "low", "close", "ask", "bid"]

print(resampled_df)
