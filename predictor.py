import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def prepare_features(df):
    data = df.copy()
    
    # --- 特徴量の作成 ---
    # 1. 移動平均乖離率
    data['MA5_Gap'] = (data['Close'] - data['Close'].rolling(5).mean()) / data['Close'].rolling(5).mean()
    data['MA25_Gap'] = (data['Close'] - data['Close'].rolling(25).mean()) / data['Close'].rolling(25).mean()
    
    # 2. ボリンジャーバンド (25日, 2σ)
    ma25 = data['Close'].rolling(25).mean()
    std25 = data['Close'].rolling(25).std()
    data['BB_Upper'] = ma25 + (std25 * 2)
    data['BB_Lower'] = ma25 - (std25 * 2)
    # 現在値がバンドのどの位置にいるか（%B：1.0なら上限、0.0なら下限）
    data['BB_Position'] = (data['Close'] - data['BB_Lower']) / (data['BB_Upper'] - data['BB_Lower'])
    
    # 3. 前日比
    data['Return'] = data['Close'].pct_change()

    # 答え合わせ用（翌日の騰落）
    data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
    
    return data.dropna()

def run_prediction(ticker):
    df = yf.download(ticker, period="5y", progress=False)
    if len(df) < 100:
        return None, None, None
    
    if hasattr(df.columns, 'levels'):
        df.columns = df.columns.get_level_values(0)

    processed_df = prepare_features(df)
    
    # 使う指標のリスト
    feature_names = ['MA5_Gap', 'MA25_Gap', 'BB_Position', 'Return']
    X = processed_df[feature_names]
    y = processed_df['Target']
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X[:-1], y[:-1])
    
    # 予測
    latest_data = X.tail(1)
    prediction = model.predict(latest_data)[0]
    confidence = model.predict_proba(latest_data)[0][prediction]
    
    # --- XAI: 特徴量の重要度を取得 ---
    importances = dict(zip(feature_names, model.feature_importances_))
    
    return prediction, confidence, importances