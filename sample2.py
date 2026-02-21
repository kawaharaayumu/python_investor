import yfinance as yf
import mplfinance as mpf

# 1. データの取得
ticker = "AMZN"
df = yf.download(ticker, start="2026-01-01", end="2026-01-31", interval="1d")

# 【ここが重要！】列の階層を1つ消して、単純な ['Open', 'High', 'Low', 'Close'...] に変換
df.columns = df.columns.get_level_values(0)

# 2. ローソク足の表示
# これでエラーなく動くはずです！
mpf.plot(df, type='candle', style='charles', 
         mav=(5,25),
         title=f"{ticker} Candlestick", 
         ylabel='Price ($)', 
         volume=True)