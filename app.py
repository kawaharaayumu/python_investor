import yfinance as yf
import mplfinance as mpf
import streamlit as st
import datetime

# --- 履歴の初期化 ---
if 'history' not in st.session_state:
    st.session_state['history'] = ["AMZN", "TSLA", "AAPL", "7203.T", "6758.T"]

st.set_page_config(page_title="Stock Analyzer", layout="wide") # 画面を広く使う
st.title("Stock Price Analyzer 📈")

# --- サイドバーの設定エリア ---
st.sidebar.header("検索設定")

# 1. 銘柄選択（プルダウン）
selected_ticker = st.sidebar.selectbox(
    "履歴・候補から選択",
    options=["-- 新しく入力 --"] + st.session_state['history']
)

# 直接入力が必要な場合のみテキストボックスを表示
if selected_ticker == "-- 新しく入力 --":
    ticker = st.sidebar.text_input("銘柄コードを入力 (例: NVDA)", value="")
else:
    ticker = selected_ticker

# 2. 期間設定 (GUIカレンダーのみ)
# 昨年の1月1日から今日までをデフォルトにする
today = datetime.date.today()
last_year = today.replace(year=today.year - 1)

st.sidebar.subheader("期間指定")
start_date = st.sidebar.date_input("開始日", value=last_year)
end_date = st.sidebar.date_input("終了日", value=today)

# 実行ボタン
search_button = st.sidebar.button("チャートを更新", type="primary")

# --- メイン画面：チャート表示エリア ---
if search_button and ticker:
    with st.spinner(f'{ticker} のデータを取得中...'):
        df = yf.download(ticker, start=start_date, end=end_date, interval="1d")

        if not df.empty:
            # 履歴に追加
            if ticker not in st.session_state['history']:
                st.session_state['history'].insert(0, ticker)
            
            # MultiIndex対策
            if hasattr(df.columns, 'levels'):
                df.columns = df.columns.get_level_values(0)

            # グラフ作成
            fig, axlist = mpf.plot(
                df, type='candle', style='charles', 
                mav=(5, 25, 75), # 75日線も追加してより本格的に
                volume=True, 
                title=f"\n{ticker} Daily Chart",
                returnfig=True, figsize=(15, 10)
            )
            st.pyplot(fig)
            
            # 数値データの表示（折りたたみ式）
            with st.expander("数値データを確認"):
                st.write(df.tail(30)) # 直近30日分
        else:
            st.error(f"'{ticker}' のデータが見つかりませんでした。")
elif not ticker:
    st.info("左側のサイドバーから銘柄を選択、または入力して「チャートを更新」を押してください。")

# 履歴リセット（サイドバー下部）
if st.sidebar.button("履歴クリア"):
    st.session_state['history'] = ["AMZN", "TSLA"]
    st.rerun()