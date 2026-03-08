import yfinance as yf
import mplfinance as mpf
import streamlit as st
import pandas as pd
import datetime
import os
import numpy as np
from streamlit_local_storage import LocalStorage
import predictor
import explain_string

st.set_page_config(page_title="Stock Analyzer", layout="wide")

# ローカルストレージの初期化
localS = LocalStorage()

# --- 1. マスターデータの読み込み (CSV) ---
@st.cache_data
def load_base_stocks():
    if os.path.exists("jpx_stocks.csv"):
        return pd.read_csv("jpx_stocks.csv")
    else:
        return pd.DataFrame({'code':['AMZN'], 'name':['Amazon'], 'display':['Amazon (AMZN)']})

base_df = load_base_stocks()

# --- 2. ローカルストレージから「個人追加分」を取得 ---
custom_stocks = localS.getItem("custom_stocks")
if custom_stocks is None:
    custom_stocks = []

# --- 3. マスターと個人分を合体させる ---
if custom_stocks:
    custom_df = pd.DataFrame(custom_stocks)
    full_df = pd.concat([custom_df, base_df], ignore_index=True).drop_duplicates(subset=['code'])
else:
    full_df = base_df

# セッション状態の初期化
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'active_ticker' not in st.session_state:
    st.session_state['active_ticker'] = None
if 'active_name' not in st.session_state:
    st.session_state['active_name'] = None
# 履歴からの選択状態を管理する変数
if 'selected_from_history' not in st.session_state:
    st.session_state['selected_from_history'] = []

st.title("Stock Price Analyzer 📈")

# --- 💡 グラフの見方ガイド ---
with st.expander("📖 グラフの見方・用語解説"):
    st.markdown(explain_string.how_to_watch, unsafe_allow_html=True)

# --- サイドバー ---
st.sidebar.header("🔍 銘柄検索")

# 【UX改善】検索ボックス
selected_list = st.sidebar.multiselect(
    "銘柄を選択（入力して検索）",
    options=full_df['display'].tolist(),
    default=st.session_state['selected_from_history'],
    max_selections=1,
    placeholder="銘柄名を入力してください...",
    key="main_selector" 
)

# 更新ボタン
search_button = st.sidebar.button("📊 チャートを更新", type="primary")

# --- 最近見た銘柄の表示 ---
st.sidebar.markdown("---")
st.sidebar.subheader("🕒 最近見た銘柄")

if st.session_state['history']:
    for h_name, h_code in st.session_state['history']:
        if st.sidebar.button(f"{h_name} ({h_code})", key=f"h_{h_code}"):
            h_display = full_df[full_df['code'] == h_code]['display'].iloc[0]
            st.session_state['selected_from_history'] = [h_display]
            st.rerun()
else:
    st.sidebar.write("履歴はまだありません")

# --- 銘柄確定ロジック ---
if selected_list:
    selected_display = selected_list[0]
    st.session_state['selected_from_history'] = [selected_display]
    
    target_row = full_df[full_df['display'] == selected_display].iloc[0]
    
    if search_button:
        st.session_state['active_ticker'] = target_row['code']
        st.session_state['active_name'] = target_row['name']
        
        hist_item = (st.session_state['active_name'], st.session_state['active_ticker'])
        if hist_item in st.session_state['history']:
            st.session_state['history'].remove(hist_item)
        st.session_state['history'].insert(0, hist_item)
        st.session_state['history'] = st.session_state['history'][:5]
else:
    st.session_state['active_ticker'] = None
    st.session_state['active_name'] = None
    st.session_state['selected_from_history'] = []

ticker = st.session_state['active_ticker']
display_name = st.session_state['active_name']

# --- 期間設定 ---
st.sidebar.markdown("---")
period_options = {"1ヶ月": 30, "3ヶ月": 90, "6ヶ月": 180, "1年": 365, "2年": 730, "5年": 1825}
selected_period_label = st.sidebar.selectbox("期間を選択", options=list(period_options.keys()), index=3)
days = period_options[selected_period_label]
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=days)

# --- カスタム追加機能 ---
with st.sidebar.expander("➕ 自分専用リストに追加"):
    new_name = st.text_input("銘柄名")
    new_code = st.text_input("コード")
    if st.button("保存"):
        if new_name and new_code:
            new_item = {'code': new_code, 'name': new_name, 'display': f"{new_name} ({new_code}) *"}
            custom_stocks.insert(0, new_item)
            localS.setItem("custom_stocks", custom_stocks)
            st.success("保存しました！")
            st.rerun()

# --- メイン表示エリア ---
if ticker:
    st.subheader(f"📊 {display_name} ({ticker})")
    df = yf.download(ticker, start=start_date, end=end_date)
    
    if not df.empty:
        stock_info = predictor.get_stock_info(ticker)
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)

        df['MA25_display'] = df['Close'].rolling(25).mean()
        df['STD25_display'] = df['Close'].rolling(25).std()
        df['Upper'] = df['MA25_display'] + (df['STD25_display'] * 2)
        df['Lower'] = df['MA25_display'] - (df['STD25_display'] * 2)
        
        has_bands = not df['Upper'].isnull().all()
        df_plot = df.dropna(subset=['Upper', 'Lower']) if has_bands else df

        add_plots = []
        if not df_plot.empty and has_bands:
            add_plots.append(mpf.make_addplot(df_plot['Upper'], color='gray', alpha=0.3))
            add_plots.append(mpf.make_addplot(df_plot['Lower'], color='gray', alpha=0.3))

        div_history = stock_info.get("配当履歴", pd.Series())
        vlines_list = []
        if not div_history.empty:
            if div_history.index.tz is not None:
                div_history.index = div_history.index.tz_localize(None)
            p_idx = df_plot.index.tz_localize(None) if df_plot.index.tz else df_plot.index
            relevant_divs = div_history[(div_history.index >= p_idx[0]) & (div_history.index <= p_idx[-1])]
            vlines_list = [date for date in relevant_divs.index]

        plot_kwargs = dict(type='candle', style='yahoo', mav=(5, 25, 75), mavcolors=('blue', 'red', 'green'),
                           volume=True, returnfig=True, figsize=(15, 8))
        if add_plots: plot_kwargs['addplot'] = add_plots
        if vlines_list: plot_kwargs['vlines'] = dict(vlines=vlines_list, colors='orange', alpha=0.7)

        fig, axlist = mpf.plot(df_plot, **plot_kwargs)
        axlist[0].set_title(f"{ticker} Analysis", fontsize=16, loc='left')
        st.pyplot(fig)

        # --- 指標表示 ---
        st.subheader(f"🏢 {display_name} の企業分析指標")
        c1, c2, c3 = st.columns(3)
        with c1:
            per = stock_info["PER"]
            st.metric("PER (株価収益率)", f"{per:.2f} 倍" if per != "---" else "---")
        with c2:
            pbr = stock_info["PBR"]
            st.metric("PBR (株価純資産倍率)", f"{pbr:.2f} 倍" if pbr != "---" else "---")
        with c3:
            y_val = stock_info["配当利回り"]
            d_yield = y_val * 100 if (y_val is not None and y_val < 1.0) else (y_val if y_val else 0)
            l_date = div_history.index[-1].strftime('%Y/%m/%d') if not div_history.empty else ""
            st.metric(f"配当利回り ({l_date})" if l_date else "配当利回り", f"{d_yield:.2f} %")

        st.write("")
        c4, c5, col6 = st.columns(3)
        with c4:
            roe = stock_info["ROE"]
            st.metric("ROE (自己資本利益率)", f"{roe*100:.2f} %" if roe != "---" else "---")
        with c5:
            cap = stock_info["時価総額"]
            curr = stock_info["通貨"]
            if cap != "---" and cap is not None:
                unit = 100_000_000
                m_val = cap / unit
                disp_cap = f"{m_val/10000:.2f} 兆{curr}" if m_val >= 10000 else f"{m_val:.1f} 億{curr}"
            else: disp_cap = "---"
            st.metric("時価総額", disp_cap)
        with col6:
            ebitda = stock_info.get("EBITDA", "---")
            if ebitda != "---" and ebitda is not None:
                eb_val = ebitda / 100_000_000
                eb_disp = f"{eb_val/10000:.1f} 兆{curr}" if eb_val >= 10000 else f"{eb_val:.1f} 億{curr}"
            else: eb_disp = "---"
            st.metric("EBITDA (稼ぐ力)", eb_disp)

        ir_url = stock_info.get("IRサイト")
        if ir_url: st.link_button(f"🔗 {display_name} 公式IRサイトへ", ir_url)
        
        with st.expander("💡 投資指標の読み方・活用ガイド"):
            st.markdown(explain_string.stock_explanation, unsafe_allow_html=True)

        # --- AI予測 ---
        st.markdown("---")
        st.subheader("🤖 AIトレンド予測 & 判断根拠 (XAI)")
        with st.spinner('分析中...'):
            try:
                pred, conf, imps, vals = predictor.run_prediction(ticker)
                if pred is not None:
                    res = "📈 上昇" if pred == 1 else "📉 下落"
                    st.subheader(f"AI予測：{res} (自信度: {conf*100:.1f}%)")
                    st.info(f"🗨️ **AIの解説:** {max(imps, key=imps.get)} を最重視しました。")
                    col_ai1, col_ai2 = st.columns([1, 2])
                    with col_ai1:
                        st.write("▼ 指標の現在値")
                        st.write(f"- 5日乖離: {vals['MA5_Gap']*100:.1f}%")
                        st.write(f"- BB位置: {vals['BB_Pos']:.2f}")
                    with col_ai2:
                        imp_df = pd.DataFrame({'指標': imps.keys(), '重要度': imps.values()}).sort_values(by='重要度')
                        st.bar_chart(data=imp_df, x='指標', y='重要度', horizontal=True)
            except Exception as e:
                st.error(f"予測エラー: {e}")
                
        if st.button("過去の的中率を検証する"):
            acc = predictor.run_backtest(ticker)
            if acc:
                st.write("---")
                st.metric("過去100日の的中率", f"{acc*100:.1f} %")
else:
    st.info("左側のサイドバーから銘柄を選択し、「チャートを更新」を押してください。")