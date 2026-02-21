import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def prepare_features(df):
    """株価データから特徴量を計算する"""
    data = df.copy()
    # 終値の移動平均乖離率
    data['MA5_Gap'] = (data['Close'] - data['Close'].rolling(5).mean()) / data['Close'].rolling(5).mean()
    data['MA25_Gap'] = (data['Close'] - data['Close'].rolling(25).mean()) / data['Close'].rolling(25).mean()
    # ボラティリティ（値動きの激しさ）
    data['Vol_Sig'] = data['Close'].pct_change().rolling(5).std()
    # 答え合わせ用：明日の終値が今日より高いか（1:上昇, 0:下落）
    data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
    
    return data.dropna()

def run_prediction(ticker):
    """過去5年のデータを元に明日の予測を行う"""
    # 5年分のデータを取得
    df = yf.download(ticker, period="5y", progress=False)
    if len(df) < 100:
        return None, None
    
    # MultiIndex対策
    if hasattr(df.columns, 'levels'):
        df.columns = df.columns.get_level_values(0)

    # 特徴量作成
    processed_df = prepare_features(df)
    
    features = ['MA5_Gap', 'MA25_Gap', 'Vol_Sig']
    X = processed_df[features]
    y = processed_df['Target']
    
    # 学習（直近の1日は答えがないので除外して学習）
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X[:-1], y[:-1])
    
    # 最新のデータで明日を予測
    latest_data = X.tail(1)
    prediction = model.predict(latest_data)[0]
    probabilities = model.predict_proba(latest_data)[0]
    
    return prediction, probabilities[prediction]