import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def prepare_features(df):
    """株価データから特徴量を計算する"""
    data = df.copy()
    
    # --- 特徴量の作成 ---
    # 1. 移動平均乖離率
    data['MA5_Gap'] = (data['Close'] - data['Close'].rolling(5).mean()) / data['Close'].rolling(5).mean()
    data['MA25_Gap'] = (data['Close'] - data['Close'].rolling(25).mean()) / data['Close'].rolling(25).mean()
    
    # 2. ボリンジャーバンド (25日, 2σ)
    ma25 = data['Close'].rolling(25).mean()
    std25 = data['Close'].rolling(25).std()
    upper = ma25 + (std25 * 2)
    lower = ma25 - (std25 * 2)
    # 現在値がバンドのどの位置にいるか（1.0なら上限、0.0なら下限）
    data['BB_Pos'] = (data['Close'] - lower) / (upper - lower)
    
    # 3. 前日比
    data['Return'] = data['Close'].pct_change()

    # 答え合わせ用：明日の終値が今日より高いか（1:上昇, 0:下落）
    data['Target'] = (data['Close'].shift(-1) > data['Close']).astype(int)
    
    return data.dropna()

def run_prediction(ticker):
    """過去5年のデータを元に明日の予測を行う"""
    df = yf.download(ticker, period="5y", progress=False)
    
    if len(df) < 100:
        return None, None, None # ここも3つ返すように修正
    
    # MultiIndex対策
    if hasattr(df.columns, 'levels'):
        df.columns = df.columns.get_level_values(0)

    # 特徴量作成
    processed_df = prepare_features(df)
    
    # 指標リスト
    feature_names = ['MA5_Gap', 'MA25_Gap', 'BB_Pos', 'Return']
    X = processed_df[feature_names]
    y = processed_df['Target']
    
    # 学習
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X[:-1], y[:-1])
    
    # 最新データで明日を予測
    latest_x = X.tail(1)
    # 1. 予測結果
    prediction = model.predict(latest_x)[0]
    # 2. 自信度
    confidence = model.predict_proba(latest_x)[0][prediction]
    # 3. 各指標の重要度 (XAI)
    importances = dict(zip(feature_names, model.feature_importances_))
    # 4. 【追加】最新の指標データそのもの
    latest_values = latest_x.iloc[0].to_dict()
    
    return prediction, confidence, importances, latest_values

def run_backtest(ticker):
    """過去100日間の予測的中率を計算する"""
    df = yf.download(ticker, period="2y", progress=False)
    if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
    
    processed_df = prepare_features(df)
    feature_names = ['MA5_Gap', 'MA25_Gap', 'BB_Pos', 'Return']
    
    # テスト対象（直近100日）
    test_days = 100
    if len(processed_df) < test_days + 50:
        return None

    results = []
    # 過去100日分、1日ずつずらしながら学習と予測を繰り返す（簡易バックテスト）
    for i in range(test_days, 0, -1):
        train_data = processed_df.iloc[:-i-1]
        test_point = processed_df.iloc[-i-1 : -i] # その日のデータ
        actual_next_move = processed_df.iloc[-i]['Target'] # 実際の翌日の動き
        
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(train_data[feature_names], train_data['Target'])
        
        pred = model.predict(test_point[feature_names])[0]
        results.append(pred == actual_next_move)
    
    accuracy = sum(results) / len(results)
    return accuracy