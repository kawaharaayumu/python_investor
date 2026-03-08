import yfinance as yf
import mplfinance as mpf
import streamlit as st
import pandas as pd
import datetime
import os
import numpy as np
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
# 表示中の銘柄を確定させるためのセッション状態
if 'active_ticker' not in st.session_state:
    st.session_state['active_ticker'] = None
if 'active_name' not in st.session_state:
    st.session_state['active_name'] = None

st.title("Stock Price Analyzer 📈")

# --- 💡 グラフの見方ガイド ---
with st.expander("📖 グラフの見方・用語解説"):
    st.markdown("""
    ### 1. ローソク足チャートの詳細
    1本の棒（ローソク）が、ある期間（1日）の「始値・高値・安値・終値」を表します。
    - **本体（太い部分）**: **「始値」と「終値」**の差。緑は上昇、赤は下落。
    - **ヒゲ（細い線）**: その日の**「高値」と「安値」**。
    ### 2. 移動平均線 (MA) の色
    - <span style="color:#0000FF">■</span> **5日線**: 青色。短期的な勢い。
    - <span style="color:#FF0000">■</span> **25日線**: 赤色。1ヶ月の平均。
    - <span style="color:#00FF00">■</span> **75日線**: 緑色。3ヶ月のトレンド。
    ### 3. 下段：出来高（Volume）
    売買の活発さ。株価上昇時に増えていれば上昇に信頼性があります。
    ### 4. ボリンジャーバンド (グレーの境界線)
    株価が統計的に収まりやすい枠。±2σを反転や加速の目安にします。
    ### 5. 配当権利落ち日 (オレンジの垂直線)
    チャート上のオレンジ色の線は配当落ち日です。この日以降、株価が調整されやすくなります。
    """, unsafe_allow_html=True)

# --- サイドバー ---
st.sidebar.header("🔍 銘柄検索")

# 【UX改善】バツ印で消せるマルチセレクト（1件制限）
selected_list = st.sidebar.multiselect(
    "銘柄を選択（入力して検索）",
    options=full_df['display'].tolist(),
    max_selections=1,
    placeholder="銘柄名を入力してください...",
    key="main_selector"
)

# 更新ボタン
search_button = st.sidebar.button("チャートを更新", type="primary")

# --- 銘柄確定ロジック (即時変更の防止) ---
if selected_list:
    selected_display = selected_list[0]
    target_row = full_df[full_df['display'] == selected_display].iloc[0]
    
    # ボタンが押された時だけ表示銘柄を更新
    if search_button:
        st.session_state['active_ticker'] = target_row['code']
        st.session_state['active_name'] = target_row['name']
        
        # 履歴の更新
        hist_item = (st.session_state['active_name'], st.session_state['active_ticker'])
        if hist_item in st.session_state['history']:
            st.session_state['history'].remove(hist_item)
        st.session_state['history'].insert(0, hist_item)
        st.session_state['history'] = st.session_state['history'][:5]
else:
    # 検索ボックスがバツ印で空になった場合
    st.session_state['active_ticker'] = None
    st.session_state['active_name'] = None

# 表示用変数にセット
ticker = st.session_state['active_ticker']
display_name = st.session_state['active_name']

# --- 最近見た銘柄の表示 ---
st.sidebar.markdown("---")
st.sidebar.subheader("🕒 最近見た銘柄")
if st.session_state['history']:
    for h_name, h_code in st.session_state['history']:
        if st.sidebar.button(f"{h_name} ({h_code})", key=f"h_{h_code}"):
            st.session_state['active_ticker'] = h_code
            st.session_state['active_name'] = h_name
            st.rerun()
else:
    st.sidebar.write("履歴はまだありません")

# --- 期間設定 (サイドバー) ---
st.sidebar.markdown("---")
st.sidebar.subheader("📅 表示期間")
period_options = {
    "1ヶ月": 30, "3ヶ月": 90, "6ヶ月": 180, "1年": 365, "2年": 730, "5年": 1825
}
selected_period_label = st.sidebar.selectbox(
    "期間を選択", options=list(period_options.keys()), index=3
)
days = period_options[selected_period_label]
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=days)

# --- 永続追加機能 ---
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
                'display': f"{new_name} ({new_code}) *"
            }
            custom_stocks.insert(0, new_item)
            localS.setItem("custom_stocks", custom_stocks)
            st.success("保存しました！")
            st.rerun()

# --- メイン表示エリア ---
if ticker:
    st.subheader(f"📊 {display_name} ({ticker})")
    
    # データ取得
    df = yf.download(ticker, start=start_date, end=end_date)
    
    if not df.empty:
        # 企業情報の取得
        stock_info = predictor.get_stock_info(ticker)
        
        # MultiIndex対策
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)

        # ボリンジャーバンド計算
        df['MA25_display'] = df['Close'].rolling(25).mean()
        df['STD25_display'] = df['Close'].rolling(25).std()
        df['Upper'] = df['MA25_display'] + (df['STD25_display'] * 2)
        df['Lower'] = df['MA25_display'] - (df['STD25_display'] * 2)
        
        has_bands = not df['Upper'].isnull().all()
        if has_bands:
            df_plot = df.dropna(subset=['Upper', 'Lower'])
        else:
            df_plot = df

        add_plots = []
        if not df_plot.empty and has_bands:
            add_plots.append(mpf.make_addplot(df_plot['Upper'], color='gray', alpha=0.3))
            add_plots.append(mpf.make_addplot(df_plot['Lower'], color='gray', alpha=0.3))

        # 配当マーク（垂直線）
        div_history = stock_info.get("配当履歴", pd.Series())
        vlines_list = []
        if not div_history.empty:
            if div_history.index.tz is not None:
                div_history.index = div_history.index.tz_localize(None)
            
            p_idx = df_plot.index
            if p_idx.tz is not None:
                p_idx = p_idx.tz_localize(None)

            relevant_divs = div_history[(div_history.index >= p_idx[0]) & 
                                        (div_history.index <= p_idx[-1])]
            vlines_list = [date for date in relevant_divs.index]

        # グラフ描画
        plot_kwargs = dict(
            type='candle', style='yahoo', mav=(5, 25, 75), 
            mavcolors=('blue', 'red', 'green'), volume=True, 
            returnfig=True, figsize=(15, 8)
        )
        if add_plots:
            plot_kwargs['addplot'] = add_plots
        if vlines_list:
            plot_kwargs['vlines'] = dict(vlines=vlines_list, colors='orange', alpha=0.7, linestyle='-')

        fig, axlist = mpf.plot(df_plot, **plot_kwargs)
        axlist[0].set_title(f"{ticker} Analysis", fontsize=16, loc='left') # 文字化け防止のため英字
        st.pyplot(fig)

        # --- 企業分析指標（3列2段） ---
        st.subheader(f"🏢 {display_name} の企業分析指標")

        col1, col2, col3 = st.columns(3)
        with col1:
            per = stock_info["PER"]
            st.metric("PER (株価収益率)", f"{per:.2f} 倍" if per != "---" else "---")
        with col2:
            pbr = stock_info["PBR"]
            st.metric("PBR (株価純資産倍率)", f"{pbr:.2f} 倍" if pbr != "---" else "---")
        with col3:
            yield_val = stock_info["配当利回り"]
            d_yield = yield_val * 100 if (yield_val is not None and yield_val < 1.0) else (yield_val if yield_val else 0)
            last_date = div_history.index[-1].strftime('%Y/%m/%d') if not div_history.empty else ""
            label = f"配当利回り ({last_date})" if last_date else "配当利回り"
            st.metric(label, f"{d_yield:.2f} %")

        st.write("") # 2段目のための隙間

        col4, col5, col6 = st.columns(3)
        with col4:
            roe = stock_info["ROE"]
            st.metric("ROE (自己資本利益率)", f"{roe*100:.2f} %" if roe != "---" else "---")
        with col5:
            cap = stock_info["時価総額"]
            currency = stock_info["通貨"]
            if cap != "---" and cap is not None:
                unit = 100_000_000
                main_val = cap / unit
                if main_val >= 10000:
                    display_cap = f"{main_val/10000:.2f} 兆{currency}"
                else:
                    display_cap = f"{main_val:.1f} 億{currency}"
            else:
                display_cap = "---"
            st.metric("時価総額", display_cap)
        with col6:
            ebitda = stock_info.get("EBITDA", "---")
            if ebitda != "---" and ebitda is not None:
                eb_val = ebitda / 100_000_000
                eb_disp = f"{eb_val/10000:.1f} 兆{currency}" if eb_val >= 10000 else f"{eb_val:.1f} 億{currency}"
            else:
                eb_disp = "---"
            st.metric("EBITDA (稼ぐ力)", eb_disp)

        ir_url = stock_info.get("IRサイト")
        if ir_url:
            st.link_button(f"🔗 {display_name} 公式IRサイトへ", ir_url)

        with st.expander("💡 投資指標の読み方・活用ガイド"):
            st.markdown("""
            ### 1. 割安さを測る（バリュー指標）
            - **PER**: 15倍が目安。製造業などで10倍を切ると「超割安」。
            - **PBR**: 1倍が底値の目安。1倍を割ると資産価値より安い状態。
            ### 2. 稼ぐ力と効率（クオリティ指標）
            - **ROE**: **8〜10%以上**なら合格点。効率よく稼いでいる証拠。
            - **EBITDA**: 本業の稼ぐ力。設備投資の影響を除外して評価可能。
            ### 3. 株主への還元（インカム指標）
            - **配当利回り**: 3%超で高配当。オレンジ垂直線後は配当落ちによる下落に注意。
            ---
            **「低PER × 高ROE」**などは、効率が良いのに割安な「お宝株」の可能性があります。
            """)
        
        # --- AI予測セクション ---
        st.markdown("---")
        st.subheader("🤖 AIトレンド予測 & 判断根拠 (XAI)")
        with st.spinner('AIが分析中...'):
            try:
                pred, conf, imps, vals = predictor.run_prediction(ticker)
                if pred is not None:
                    res_txt = "📈 上昇" if pred == 1 else "📉 下落"
                    st.subheader(f"AI予測：{res_txt} (自信度: {conf*100:.1f}%)")

                    top_feature = max(imps, key=imps.get)
                    comments = []
                    if top_feature == 'MA5_Gap':
                        val = vals['MA5_Gap'] * 100
                        comments.append(f"AIは「5日移動平均線からの乖離({val:.1f}%)」を最重視し、反発または調整を予測しました。")
                    elif top_feature == 'BB_Pos':
                        comments.append(f"AIは「ボリンジャーバンド内の位置」に注目し、現在の過熱感からトレンドを判断しました。")
                    elif top_feature == 'Return':
                        comments.append(f"AIは「前日の騰落勢い」が継続するパターンを過去から読み取っています。")

                    st.info(f"🗨️ **AIの解説:** {comments[0] if comments else '現在のトレンドパターンから予測を算出しました。'}")

                    col_ai1, col_ai2 = st.columns([1, 2])
                    with col_ai1:
                        st.write("▼ 指標の現在値")
                        st.write(f"- 5日乖離: {vals['MA5_Gap']*100:.1f}%")
                        st.write(f"- BB位置: {vals['BB_Pos']:.2f}")
                    with col_ai2:
                        imp_df = pd.DataFrame({'指標': imps.keys(), '重要度': imps.values()}).sort_values(by='重要度')
                        st.bar_chart(data=imp_df, x='指標', y='重要度', horizontal=True)
            except Exception as e:
                st.error(f"AI予測中にエラーが発生しました: {e}")
                
        if st.button("過去の的中率を検証する"):
            with st.spinner('過去の的中率を検証中...'):
                backtest_acc = predictor.run_backtest(ticker)
                if backtest_acc is not None:
                    st.write("---")
                    st.subheader("🎯 過去のシミュレーション結果")
                    c_bt1, c_bt2 = st.columns([1, 2])
                    with c_bt1:
                        st.metric("過去100日の的中率", f"{backtest_acc*100:.1f} %")
                    with c_bt2:
                        if backtest_acc > 0.55:
                            st.success("✅ この銘柄はAIの予測パターンが比較的適合しています。")
                        elif backtest_acc > 0.45:
                            st.warning("⚠️ 的中率は平均的です。他の指標も併用してください。")
                        else:
                            st.error("❌ 現在の相場はこのAIモデルが苦手とする不規則な動きです。")
else:
    st.info("左側のサイドバーから銘柄を選択し、「チャートを更新」を押してください。")