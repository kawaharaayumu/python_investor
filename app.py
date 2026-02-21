import yfinance as yf
import mplfinance as mpf
import streamlit as st
import pandas as pd
import datetime
import os
from streamlit_local_storage import LocalStorage
import predictor

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

# --- 【ここを追加】選択された瞬間に履歴に追加するロジック ---
if ticker:
    hist_item = (display_name, ticker)
    # すでに同じ銘柄が履歴にある場合は一度削除（最新として先頭に持ってくるため）
    if hist_item in st.session_state['history']:
        st.session_state['history'].remove(hist_item)
    
    # 履歴の先頭に追加
    st.session_state['history'].insert(0, hist_item)
    
    # 履歴は最大5件までに制限
    st.session_state['history'] = st.session_state['history'][:5]

# --- 最近見た銘柄の表示 ---
st.sidebar.markdown("---")
st.sidebar.subheader("🕒 最近見た銘柄")
if st.session_state['history']:
    for h_name, h_code in st.session_state['history']:
        # 履歴ボタンを押した時の処理
        if st.sidebar.button(f"{h_name} ({h_code})", key=f"h_{h_code}"):
            # ボタンが押されたらその銘柄を現在の表示対象にする
            ticker = h_code
            display_name = h_name
            # ※ボタンを押した際も即座に再描画させるために rerun を使うとよりスムーズです
            st.rerun()
else:
    st.sidebar.write("履歴はまだありません")

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
    
    # チャート用のデータ取得
    df = yf.download(ticker, start=start_date, end=end_date)
    
    if not df.empty:
        # 履歴更新
        hist_item = (display_name, ticker)
        if hist_item not in st.session_state['history']:
            st.session_state['history'].insert(0, hist_item)
            st.session_state['history'] = st.session_state['history'][:5]
        
        # MultiIndex対策
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)

        # --- ボリンジャーバンドの計算 (表示用) ---
        df['MA25_display'] = df['Close'].rolling(25).mean()
        df['STD25_display'] = df['Close'].rolling(25).std()
        df['Upper'] = df['MA25_display'] + (df['STD25_display'] * 2)
        df['Lower'] = df['MA25_display'] - (df['STD25_display'] * 2)
        
        # 描画用の追加設定（ボリンジャーバンドの線を設定）
        add_plots = [
            mpf.make_addplot(df['Upper'], color='gray', alpha=0.3),
            mpf.make_addplot(df['Lower'], color='gray', alpha=0.3),
        ]

        # 描画実行
        fig, _ = mpf.plot(
            df, type='candle', style='charles', 
            mav=(5, 25, 75), addplot=add_plots, 
            volume=True, returnfig=True, figsize=(15, 8)
        )
        st.pyplot(fig)
        
        # --- AI予測セクション ---
        st.markdown("---")
        st.subheader("🤖 AIトレンド予測 & 判断根拠 (XAI)")
        st.write("過去5年間のパターンから、明日の騰落と「何を重視したか」を表示します。")

        with st.spinner('AIが判断理由を分析中...'):
            try:
                # predictor.py から「予測、自信度、重要度」を受け取る
                pred_result, confidence, importances = predictor.run_prediction(ticker)
            
                if pred_result is not None:
                    col_res, col_imp = st.columns([1, 2]) # 左に結果、右にグラフ
                    
                    with col_res:
                        if pred_result == 1:
                            st.success("### 予想：📈 上昇")
                        else:
                            st.error("### 予想：📉 下落")
                        st.metric("予測の自信度", f"{confidence*100:.1f} %")
                        st.progress(float(confidence))

                    with col_imp:
                        st.write("▼ AIが重視した指標")
                        # 重要度をデータフレームにしてグラフ化
                        imp_df = pd.DataFrame({
                            '指標': importances.keys(),
                            '重要度': importances.values()
                        }).sort_values(by='重要度', ascending=True)
                        st.bar_chart(data=imp_df, x='指標', y='重要度', horizontal=True)
                
                    st.caption("※BB_Position: ボリンジャーバンド内の位置 / MA_Gap: 移動平均乖離 / Return: 前日比")
                else:
                    st.warning("データ不足のため予測できませんでした。")
            except Exception as e:
                st.error(f"予測中にエラーが発生しました: {e}")