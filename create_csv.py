import pandas as pd

# ダウンロードしたファイル名（もし .xlsx だったら書き換えてください）
excel_file = "data_j.xls" 

print(f"{excel_file} を読み込んでいます...")
df = pd.read_excel(excel_file)

# 必要な列を作り、整形する（日本の銘柄コードには .T をつける）
df['code'] = df['コード'].astype(str) + ".T"
df['name'] = df['銘柄名']
df['display'] = df['name'] + " (" + df['code'] + ")"

# 必要な3列だけを抽出
df_csv = df[['code', 'name', 'display']].copy()

# よく見る米国株も追加
us_stocks = pd.DataFrame({
    'code': ['AMZN', 'TSLA', 'AAPL', 'NVDA', 'MSFT', 'GOOGL'],
    'name': ['Amazon', 'Tesla', 'Apple', 'NVIDIA', 'Microsoft', 'Alphabet(Google)'],
    'display': ['Amazon (AMZN)', 'Tesla (TSLA)', 'Apple (AAPL)', 'NVIDIA (NVDA)', 'Microsoft (MSFT)', 'Alphabet(Google) (GOOGL)']
})
df_csv = pd.concat([us_stocks, df_csv], ignore_index=True)

# CSVとして保存
df_csv.to_csv("jpx_stocks.csv", index=False)
print("✅ jpx_stocks.csv の作成が完了しました！")