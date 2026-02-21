import yfinance as yf
import mplfinance as mpf
import streamlit as st
import datetime

# --- 履歴の初期化 ---
if 'history' not in st.session_state:
    st.session_state['history'] = ["AMZN", "TSLA", "AAPL", "7203.T", "6758.T"] # 初期候補

st.title("Stock Price Analyzer 📈")

# --- 銘柄選択・入力エリア ---
st.write("### 銘柄選択")

# 1. プルダウン（履歴・候補から選択）
selected_ticker = st.selectbox(
    "履歴や候補から選ぶ",
    options=["-- 新しく入力する --"] + st.session_state['history']
)

# 2. 直接入力欄
# プルダウンで「新しく入力する」以外が選ばれたら、その値を初期値にする
default_input = "" if selected_ticker == "-- 新しく入力する --" else selected_ticker
ticker = st.text_input("銘柄コードを直接入力・修正", value=default_input, placeholder="例: NVDA")

# --- 期間設定 ---
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("開始日", value=datetime.date(2025, 1, 1))
with col2:
    end_date = st.date_input("終了日", value=datetime.date(2025, 12, 31))

if st.button("チャートを表示", type="primary"):
    if ticker:
        with st.spinner('データを取得中...'):
            df = yf.download(ticker, start=start_date, end=end_date, interval="1d")

            if not df.empty:
                # 履歴に追加（重複を除いて最新を先頭に）
                if ticker not in st.session_state['history']:
                    st.session_state['history'].insert(0, ticker)
                
                # MultiIndex対策
                if hasattr(df.columns, 'levels'):
                    df.columns = df.columns.get_level_values(0)

                # グラフ作成
                fig, axlist = mpf.plot(
                    df, type='candle', style='charles', 
                    mav=(5, 25), volume=True, 
                    title=f"\n{ticker} Chart",
                    returnfig=True, figsize=(12, 8)
                )
                st.pyplot(fig)
                st.write("### 過去データ (最新5日分)", df.tail())
                
                # 履歴を即座にプルダウンに反映させるために再描画
                st.rerun()
            else:
                st.error(f"銘柄コード '{ticker}' のデータが見つかりませんでした。")
    else:
        st.warning("銘柄コードを入力してください。")

# 履歴クリア機能（サイドバー）
if st.sidebar.button("履歴をリセット"):
    st.session_state['history'] = ["AMZN", "TSLA", "AAPL"]
    st.rerun()