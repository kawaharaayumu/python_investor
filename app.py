import yfinance as yf
import mplfinance as mpf
import streamlit as st
import datetime

# --- 1. 銘柄名とコードの対応辞書 ---
# お気に入りの銘柄をここに追加していけます
STOCK_DICT = {
    "トヨタ自動車": "7203.T",
    "ソニーグループ": "6758.T",
    "ソフトバンクグループ": "9984.T",
    "任天堂": "7974.T",
    "ファーストリテイリング": "9983.T",
    "三菱UFJ FG": "8306.T",
    "Amazon": "AMZN",
    "Tesla": "TSLA",
    "Apple": "AAPL",
    "NVIDIA": "NVDA"
}

# --- 履歴の初期化 ---
if 'history_names' not in st.session_state:
    st.session_state['history_names'] = list(STOCK_DICT.keys())

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("Stock Price Analyzer 📈")

# --- サイドバーの設定エリア ---
st.sidebar.header("検索設定")

# 1. 銘柄選択（日本語名で表示）
selected_name = st.sidebar.selectbox(
    "銘柄を選択",
    options=["-- 直接コード入力 --"] + st.session_state['history_names']
)

# 2. コードの特定
if selected_name == "-- 直接コード入力 --":
    ticker = st.sidebar.text_input("銘柄コードを入力 (例: 9101.T)", value="")
    display_name = ticker
else:
    ticker = STOCK_DICT.get(selected_name, selected_name)
    display_name = selected_name

# 期間設定
today = datetime.date.today()
last_year = today.replace(year=today.year - 1)
start_date = st.sidebar.date_input("開始日", value=last_year)
end_date = st.sidebar.date_input("終了日", value=today)

search_button = st.sidebar.button("チャートを更新", type="primary")

# --- メイン画面 ---
if search_button and ticker:
    with st.spinner(f'{display_name} ({ticker}) のデータを取得中...'):
        df = yf.download(ticker, start=start_date, end=end_date, interval="1d")

        if not df.empty:
            # 新しい銘柄コードが入力された場合、辞書と履歴に追加
            if selected_name == "-- 直接コード入力 --" and ticker not in STOCK_DICT.values():
                # 本来は会社名を取得したいが、簡易的にコードを名前として保存
                STOCK_DICT[ticker] = ticker 
                if ticker not in st.session_state['history_names']:
                    st.session_state['history_names'].insert(0, ticker)
            
            # MultiIndex対策
            if hasattr(df.columns, 'levels'):
                df.columns = df.columns.get_level_values(0)

            # グラフ作成
            fig, axlist = mpf.plot(
                df, type='candle', style='charles', 
                mav=(5, 25, 75), 
                volume=True, 
                title=f"\n{display_name} ({ticker})",
                returnfig=True, figsize=(15, 10)
            )
            st.pyplot(fig)
            
            with st.expander("数値データを確認"):
                st.write(df.tail(30))
        else:
            st.error(f"'{ticker}' のデータが見つかりませんでした。")