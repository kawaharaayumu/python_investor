import yfinance as yf
import matplotlib.pyplot as plt

# yf.download(対象の株銘柄、期間、頻度)
ticker = "AMZN"
# ticker = ["6758.T","7203.T"]
# sony 6758.T
# トヨタ 7203.T
# 

# df = yf.download(ticker, period="1mo",interval="1d")
df = yf.download(ticker, start="2024-12-01", end = "2024-12-31", interval="1d")
df.columns = ["Close", "High", "Low", "Open", "Volume"]
# Close 終値　hige たかね　LOW 安値　Open はじめ　Volume 出来高　どれくらい取引されたか
# print(df.head())
# print(df)

df = df.drop("Volume", axis=1)
plt.figure(figsize=(15,6))
plt.plot(df.index, df)
plt.legend(df)
plt.show()
