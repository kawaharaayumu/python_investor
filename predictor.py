import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import streamlit as st

def prepare_features(df, per=None, pbr=None):
    """株価データと財務指標から特徴量を計算する"""
    data = df.copy()
    
    # 既存のテクニカル指標
    data['MA5_Gap'] = (data['Close'] - data['Close'].rolling(5).mean()) / data['Close'].rolling(5).mean()
    data['MA25_Gap'] = (data['Close'] - data['Close'].rolling(25).mean()) / data['Close'].rolling(25).mean()
    
    ma25 = data['Close'].rolling(25).mean()
    std25 = data['Close'].rolling(25).std()
    data['BB_Pos'] = (data['Close'] - (ma25 - std25*2)) / ((ma25 + std25*2) - (ma25 - std25*2))
    data['Return'] = data['Close'].pct_change()

    # --- 【追加】財務指標 ---
    # 数値がない場合は、平均的な値（PER 15, PBR 1）で埋める
    data['PER_Val'] = per if (per and per != "---") else 15.0
    data['PBR_Val'] = pbr if (pbr and pbr != "---") else 1.0

    data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
    return data.dropna()

def run_prediction(ticker):
    # 先に企業情報を取得
    info = get_stock_info(ticker)
    
    df = yf.download(ticker, period="5y", progress=False)
    if len(df) < 100: return None, None, None, None
    if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)

    # 財務指標を渡して特徴量作成
    processed_df = prepare_features(df, per=info['PER'], pbr=info['PBR'])
    
    # 指標リストに PER/PBR を追加
    feature_names = ['MA5_Gap', 'MA25_Gap', 'BB_Pos', 'Return', 'PER_Val', 'PBR_Val']
    X = processed_df[feature_names]
    y = processed_df['Target']
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X[:-1], y[:-1])
    
    latest_x = X.tail(1)
    prediction = model.predict(latest_x)[0]
    confidence = model.predict_proba(latest_x)[0][prediction]
    importances = dict(zip(feature_names, model.feature_importances_))
    latest_values = latest_x.iloc[0].to_dict()
    
    return prediction, confidence, importances, latest_values

@st.cache_data(ttl=3600)  # 1時間(3600秒)はデータを再利用する
def run_backtest(ticker):
    """過去100日間の予測的中率を計算する"""
    # 1. 先に企業情報を取得（PER/PBR用）
    info = get_stock_info(ticker)
    
    df = yf.download(ticker, period="2y", progress=False)
    if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
    
    # 2. 財務指標を渡して特徴量を作成
    processed_df = prepare_features(df, per=info['PER'], pbr=info['PBR'])
    
    # 3. 学習に使う項目に PER_Val と PBR_Val を追加
    feature_names = ['MA5_Gap', 'MA25_Gap', 'BB_Pos', 'Return', 'PER_Val', 'PBR_Val']
    
    test_days = 100
    if len(processed_df) < test_days + 50:
        return None

    results = []
    for i in range(test_days, 0, -1):
        # i=100のとき、最後から101番目以前を学習データに、100番目をテストに、99番目を正解にする
        train_data = processed_df.iloc[:-i-1]
        test_point = processed_df.iloc[-i-1 : -i]
        actual_next_move = processed_df.iloc[-i]['Target']
        
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(train_data[feature_names], train_data['Target'])
        
        pred = model.predict(test_point[feature_names])[0]
        results.append(pred == actual_next_move)
    
    accuracy = sum(results) / len(results)
    return accuracy

@st.cache_data(ttl=3600)  # 1時間(3600秒)はデータを再利用する
def get_stock_info(ticker):
    t = yf.Ticker(ticker)
    info = t.info
    
    data = {
        "PER": info.get("trailingPE", "---"),
        "PBR": info.get("priceToBook", "---"),
        "配当利回り": info.get("dividendYield", 0),
        "時価総額": info.get("marketCap", "---"),
        "ROE": info.get("returnOnEquity", "---"),
        "通貨": info.get("currency", "JPY") # デフォルトは円にしておく
    }
    return data