import yfinance as yf
import mplfinance as mpf
import streamlit as st
import datetime

# Webアプリの見出し
st.title("Stock Price Analyzer 📈")

# ユーザー入力
ticker = st.text_input("銘柄コードを入力してください (例: AMZN, TSLA, 7203.T)", "AMZN")

# 期間の選択
start_date = st.date_input("開始日", value=datetime.date(2025, 1, 1))
end_date = st.date_input("終了日", value=datetime.date(2025, 12, 31))

if st.button("データ取得"):
    # データをダウンロード
    df = yf.download(ticker, start=start_date, end=end_date, interval="1d")

    if not df.empty:
        # MultiIndex対策 (最新のyfinance用)
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)

        # --- グラフの作成 ---
        # returnfig=True を指定すると、(figure, axes) のタプルが返ってきます
        fig, axlist = mpf.plot(
            df, 
            type='candle', 
            style='charles', 
            mav=(5, 25), 
            volume=True, 
            title=f"\n{ticker} Chart",
            returnfig=True,
            figsize=(12, 8)
        )
        
        # Streamlitの画面に表示
        st.pyplot(fig)
        
        # データテーブルの表示
        st.write("### 過去データ (最新5日分)", df.tail())
    else:
        st.error("データが見つかりませんでした。銘柄コードや期間を確認してください。")