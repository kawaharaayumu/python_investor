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
import sidebar  

st.set_page_config(page_title="Stock Analyzer", layout="wide")
localS = LocalStorage()

# データロード
@st.cache_data
def load_base_stocks():
    if os.path.exists("jpx_stocks.csv"):
        return pd.read_csv("jpx_stocks.csv")
    return pd.DataFrame({'code':['AMZN'], 'name':['Amazon'], 'display':['Amazon (AMZN)']})

base_df = load_base_stocks()
custom_stocks = localS.getItem("custom_stocks") or []
full_df = pd.concat([pd.DataFrame(custom_stocks), base_df], ignore_index=True).drop_duplicates(subset=['code']) if custom_stocks else base_df

# セッション状態
if 'active_ticker' not in st.session_state:
    st.session_state['active_ticker'] = None
if 'active_name' not in st.session_state:
    st.session_state['active_name'] = None

st.title("Stock Price Analyzer 📈")

with st.expander("📖 グラフの見方・用語解説"):
    st.markdown(explain_string.how_to_watch, unsafe_allow_html=True)

# --- サイドバーのレンダリング ---
selected_list, search_button, days = sidebar.render_sidebar(full_df, localS, custom_stocks)

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

# 描画用変数
ticker = st.session_state['active_ticker']
display_name = st.session_state['active_name']

# --- メイン表示エリア ---
if ticker:
    st.subheader(f"📊 {display_name} ({ticker})")
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    df = yf.download(ticker, start=start_date, end=end_date)
    
    if not df.empty:
        stock_info = predictor.get_stock_info(ticker)
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)

        # チャート作成
        df['MA25_display'] = df['Close'].rolling(25).mean()
        df['STD25_display'] = df['Close'].rolling(25).std()
        df['Upper'] = df['MA25_display'] + (df['STD25_display'] * 2)
        df['Lower'] = df['MA25_display'] - (df['STD25_display'] * 2)
        
        has_bands = not df['Upper'].isnull().all()
        df_plot = df.dropna(subset=['Upper', 'Lower']) if has_bands else df

        add_plots = [mpf.make_addplot(df_plot['Upper'], color='gray', alpha=0.3),
                     mpf.make_addplot(df_plot['Lower'], color='gray', alpha=0.3)] if has_bands else []

        div_history = stock_info.get("配当履歴", pd.Series())
        vlines_list = []
        if not div_history.empty:
            if div_history.index.tz is not None:
                div_history.index = div_history.index.tz_localize(None)
            p_idx = df_plot.index.tz_localize(None) if df_plot.index.tz else df_plot.index
            vlines_list = [date for date in div_history.index if p_idx[0] <= date <= p_idx[-1]]

        fig, axlist = mpf.plot(df_plot, type='candle', style='yahoo', mav=(5, 25, 75), 
                               mavcolors=('blue', 'red', 'green'), volume=True, 
                               addplot=add_plots, returnfig=True, figsize=(15, 8),
                               vlines=dict(vlines=vlines_list, colors='orange', alpha=0.7) if vlines_list else None)
        st.pyplot(fig)

        # 指標表示
        st.subheader(f"🏢 {display_name} の企業分析指標")
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("PER (株価収益率)", f"{stock_info['PER']:.2f} 倍" if isinstance(stock_info['PER'], (int, float)) else "---")
        with c2: st.metric("PBR (株価純資産倍率)", f"{stock_info['PBR']:.2f} 倍" if isinstance(stock_info['PBR'], (int, float)) else "---")
        with c3:
            y_val = stock_info["配当利回り"]
            d_yield = y_val * 100 if (y_val is not None and y_val < 1.0) else (y_val or 0)
            st.metric("配当利回り", f"{d_yield:.2f} %")

        # AI予測
        st.markdown("---")
        st.subheader("🤖 AIトレンド予測 & 判断根拠 (XAI)")
        try:
            pred, conf, imps, vals = predictor.run_prediction(ticker)
            if pred is not None:
                st.write(f"予測：{'📈 上昇' if pred == 1 else '📉 下落'} (自信度: {conf*100:.1f}%)")
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
else:
    st.info("左側のサイドバーから銘柄を選択し、「チャートを更新」を押してください。")