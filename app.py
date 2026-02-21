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

# --- 期間設定 (サイドバー) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📅 表示期間")

# 選択肢をリストで用意
period_options = {
    "1ヶ月": 30,
    "3ヶ月": 90,
    "6ヶ月": 180,
    "1年": 365,
    "2年": 730,
    "5年": 1825
}

# セレクトボックスで選択（キーボードが出ない）
selected_period_label = st.sidebar.selectbox(
    "期間を選択",
    options=list(period_options.keys()),
    index=3  # デフォルトで「1年」を選択
)

# 選択されたラベルから日数を取得して開始日を計算
days = period_options[selected_period_label]
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=days)

# 更新ボタン
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
        
        # 【重要】データが25日分以上あり、ボリンジャーバンドが計算できているかチェック
        add_plots = []
        if not df['Upper'].isnull().all():
            # NaNが含まれる行（最初の24日間など）をグラフ描画から除外する
            # または addplot 側でデータを整える
            df_plot = df.dropna(subset=['Upper', 'Lower'])
            
            if not df_plot.empty:
                add_plots = [
                    mpf.make_addplot(df_plot['Upper'], color='gray', alpha=0.3),
                    mpf.make_addplot(df_plot['Lower'], color='gray', alpha=0.3),
                ]
            else:
                df_plot = df # 描画対象を元に戻す
        else:
            df_plot = df

        # 描画実行 (df ではなく df_plot を使う)
        fig, _ = mpf.plot(
            df_plot, type='candle', style='charles', 
            mav=(5, 25, 75), addplot=add_plots, 
            volume=True, returnfig=True, figsize=(15, 8)
        )
        st.pyplot(fig)
        
        # --- AI予測セクション ---
        st.markdown("---")
        st.subheader("🤖 AIトレンド予測 & 判断根拠 (XAI)")
        st.write("過去5年間のパターンから、明日の騰落と「何を重視したか」を表示します。")

        # --- AI予測セクション (app.py内) ---
        with st.spinner('AIが判断理由を分析中...'):
            try:
                # predictor.py から4つのデータを受け取る
                pred, conf, imps, vals = predictor.run_prediction(ticker)
                
                if pred is not None:
                    # 1. まず結果を表示
                    res_txt = "📈 上昇" if pred == 1 else "📉 下落"
                    st.subheader(f"AI予測：{res_txt} (自信度: {conf*100:.1f}%)")

                    # 2. 自動解説コメントの生成
                    comments = []
                    
                    # 重要度が最も高い指標を特定
                    top_feature = max(imps, key=imps.get)
                    
                    # --- 指標ごとの解説ロジック ---
                    if top_feature == 'MA5_Gap':
                        val = vals['MA5_Gap'] * 100
                        status = "高く、短期的に買われすぎ" if val > 0 else "低く、短期的に売られすぎ"
                        comments.append(f"AIは「5日移動平均線からの乖離」を最も重視しました。現在は {val:.1f}% と{status}の状態で、反発の予兆を捉えています。")
                    
                    elif top_feature == 'BB_Pos':
                        val = vals['BB_Pos']
                        if val > 0.8: status = "ボリンジャーバンドの上限付近にあり、上昇圧力が強い"
                        elif val < 0.2: status = "ボリンジャーバンドの下限付近にあり、売りの限界に近い"
                        else: status = "バンドの中央付近におり、安定した推移"
                        comments.append(f"AIは「ボリンジャーバンド内の位置」に注目しました。現在は {status} と判断しています。")

                    elif top_feature == 'Return':
                        val = vals['Return'] * 100
                        comments.append(f"AIは「前日の騰落（{val:.1f}%）」の勢いが、翌日も継続（または反転）するパターンを過去の傾向から読み取っています。")

                    # コメントの表示
                    st.info(f"🗨️ **AIの解説:** {''.join(comments)}")

                    # 3. グラフ表示（以前のコードと同様）
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write("▼ 指標の現在値")
                        st.write(f"- 5日乖離: {vals['MA5_Gap']*100:.1f}%")
                        st.write(f"- BB位置: {vals['BB_Pos']:.2f}")
                    with col2:
                        imp_df = pd.DataFrame({'指標': imps.keys(), '重要度': imps.values()}).sort_values(by='重要度')
                        st.bar_chart(data=imp_df, x='指標', y='重要度', horizontal=True)

            except Exception as e:
                st.error(f"予測中にエラーが発生しました: {e}")