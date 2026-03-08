import streamlit as st
import datetime
import pandas as pd

def render_sidebar(full_df, localS, custom_stocks):
    st.sidebar.header("🔍 銘柄検索")

    # 1. セッション状態の初期化
    if 'selected_from_history' not in st.session_state:
        st.session_state['selected_from_history'] = []
    if 'history' not in st.session_state:
        st.session_state['history'] = []

    # 2. 銘柄検索（multiselectを単一選択として使用）
    # 履歴ボタンからこの変数を書き換えることで、自動入力を実現します
    selected_list = st.sidebar.multiselect(
        "銘柄を選択（入力して検索）",
        options=full_df['display'].tolist(),
        default=st.session_state['selected_from_history'],
        max_selections=1,
        placeholder="銘柄名を入力してください...",
        key="main_selector" 
    )

    # 3. チャート更新ボタン
    # このボタンを押すまで active_ticker は更新されません
    search_button = st.sidebar.button("📊 チャートを更新", type="primary")

    # 4. 最近見た銘柄（履歴）
    st.sidebar.markdown("---")
    st.sidebar.subheader("🕒 最近見た銘柄")
    if st.session_state['history']:
        for h_name, h_code in st.session_state['history']:
            if st.sidebar.button(f"{h_name} ({h_code})", key=f"h_{h_code}"):
                # 該当銘柄の表示名を取得
                h_display = full_df[full_df['code'] == h_code]['display'].iloc[0]
                # セッション状態を更新して再描画（入力ボックスに値が入る）
                st.session_state['selected_from_history'] = [h_display]
                st.rerun()
    else:
        st.sidebar.write("履歴はまだありません")

    # 5. 表示期間の設定
    st.sidebar.markdown("---")
    period_options = {"1ヶ月": 30, "3ヶ月": 90, "6ヶ月": 180, "1年": 365, "2年": 730, "5年": 1825}
    selected_period_label = st.sidebar.selectbox("期間を選択", options=list(period_options.keys()), index=3)
    days = period_options[selected_period_label]
    
    # 6. 自分専用リストに追加
    st.sidebar.markdown("---")
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

    return selected_list, search_button, days