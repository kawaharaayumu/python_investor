import yfinance as yf
import mplfinance as mpf
import streamlit as st
import pandas as pd
import datetime
import os
from streamlit_local_storage import LocalStorage

st.set_page_config(page_title="Stock Analyzer", layout="wide")

# ローカルストレージの初期化
localS = LocalStorage()

# --- 1. マスターデータの読み込み (CSV) ---
@st.cache_data
def load_base_stocks():
    if os.path.exists("jpx_stocks.csv"):
        return pd.read_csv("jpx_stocks.csv")
    else:
        # CSVがない場合の最低限のバックアップ
        return pd.DataFrame({'code':['AMZN'], 'name':['Amazon'], 'display':['Amazon (AMZN)']})

base_df = load_base_stocks()

# --- 2. ローカルストレージから「個人追加分」を取得 ---
# 'custom_stocks' というキーで保存されていると仮定
custom_stocks = localS.getItem("custom_stocks")
if custom_stocks is None:
    custom_stocks = [] # 初回は空リスト

# --- 3. マスターと個人分を合体させる ---
if custom_stocks:
    custom_df = pd.DataFrame(custom_stocks)
    # 合体（個人追加分を上にする）
    full_df = pd.concat([custom_df, base_df], ignore_index=True).drop_duplicates(subset=['code'])
else:
    full_df = base_df

# セッション状態で管理
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.title("Stock Price Analyzer 📈")

# --- サイドバー ---
st.sidebar.header("🔍 銘柄検索")

# 検索付きプルダウン
selected_display = st.sidebar.selectbox(
    "銘柄を選択（入力して検索）",
    options=full_df['display'].tolist()
)

# 選択されたコードを取得
target_row = full_df[full_df['display'] == selected_display].iloc[0]
ticker = target_row['code']
display_name = target_row['name']

# --- 最近見た銘柄 (Session State) ---
st.sidebar.markdown("---")
st.sidebar.subheader("🕒 最近見た銘柄")
for h_name, h_code in st.session_state['history']:
    if st.sidebar.button(f"{h_name} ({h_code})", key=f"h_{h_code}"):
        ticker = h_code
        display_name = h_name

# --- 期間設定 ---
st.sidebar.markdown("---")
start_date = st.sidebar.date_input("開始日", value=datetime.date.today() - datetime.timedelta(days=365))
end_date = st.sidebar.date_input("終了日", value=datetime.date.today())
search_button = st.sidebar.button("チャートを更新", type="primary")

# --- 【重要】銘柄の「永続」追加機能 ---
st.sidebar.markdown("---")
with st.sidebar.expander("➕ 自分専用リストに追加"):
    st.write("ここに追加するとブラウザに保存されます")
    new_name = st.text_input("銘柄名 (例: Google)")
    new_code = st.text_input("コード (例: GOOGL)")
    if st.button("保存"):
        if new_name and new_code:
            new_item = {
                'code': new_code, 
                'name': new_name, 
                'display': f"{new_name} ({new_code}) *" # 自分追加分とわかるように印
            }
            # 既存のカスタムリストに追加して保存
            custom_stocks.insert(0, new_item)
            localS.setItem("custom_stocks", custom_stocks)
            st.success("ブラウザに保存しました！")
            st.rerun()

# --- メイン表示 ---
if search_button or ticker:
    st.subheader(f"📊 {display_name} ({ticker})")
    df = yf.download(ticker, start=start_date, end=end_date)
    if not df.empty:
        # 履歴更新
        if (display_name, ticker) not in st.session_state['history']:
            st.session_state['history'].insert(0, (display_name, ticker))
            st.session_state['history'] = st.session_state['history'][:5]
        
        # カラム調整
        if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
        
        # 描画
        fig, _ = mpf.plot(df, type='candle', style='charles', mav=(5, 25), volume=True, returnfig=True, figsize=(15, 8))
        st.pyplot(fig)