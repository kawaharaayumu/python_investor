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

# 世界のトップ企業・有名企業を追加
global_stocks = pd.DataFrame({
    'code': [
        'AMZN', 'TSLA', 'AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META',  # 米国IT（マグニフィセント7）
        'AVGO', 'ASML', 'TSM',                                   # 半導体巨頭（ブロードコム、ASML、TSMC）
        'BRK-B', 'V', 'MA',                                      # 金融・決済（バークシャー、VISA、マスターカード）
        'LLY', 'NVO', 'JNJ',                                     # ヘルスケア（イーライリリー、ノボノルディスク、J&J）
        'WMT', 'KO', 'PEP', 'SBUX',                              # 消費財（ウォルマート、コカコーラ、ペプシ、スタバ）
        'MC.PA', 'RMS.PA',                                       # 欧州ブランド（LVMH、エルメス ※通貨EUR）
        'NKE', 'DIS'                                             # スポーツ・エンタメ（ナイキ、ディズニー）
    ],
    'name': [
        'Amazon', 'Tesla', 'Apple', 'NVIDIA', 'Microsoft', 'Alphabet', 'Meta',
        'Broadcom', 'ASML', 'TSMC',
        'Berkshire Hathaway', 'Visa', 'Mastercard',
        'Eli Lilly', 'Novo Nordisk', 'J&J',
        'Walmart', 'Coca-Cola', 'PepsiCo', 'Starbucks',
        'LVMH', 'Hermès',
        'Nike', 'Disney'
    ],
    'display': [
        'Amazon (AMZN)', 'Tesla (TSLA)', 'Apple (AAPL)', 'NVIDIA (NVDA)', 'Microsoft (MSFT)', 'Alphabet (GOOGL)', 'Meta (META)',
        'Broadcom (AVGO)', 'ASML (ASML)', 'TSMC (TSM)',
        'Berkshire Hathaway (BRK-B)', 'Visa (V)', 'Mastercard (MA)',
        'Eli Lilly (LLY)', 'Novo Nordisk (NVO)', 'J&J (JNJ)',
        'Walmart (WMT)', 'Coca-Cola (KO)', 'PepsiCo (PEP)', 'Starbucks (SBUX)',
        'LVMH (MC.PA)', 'Hermès (RMS.PA)',
        'Nike (NKE)', 'Disney (DIS)'
    ]
})

# ソフトウェア・デジタルトランスフォーメーション企業を追加
software_global_stocks = pd.DataFrame({
    'code': [
        'CRM', 'SAP', 'SIE.DE', 'NOW', 'ADBE', 'ORCL', 'INTU', 'PANW', 'SNOW'
    ],
    'name': [
        'Salesforce', 'SAP', 'Siemens', 'ServiceNow', 'Adobe', 'Oracle', 'Intuit', 'Palo Alto Networks', 'Snowflake'
    ],
    'display': [
        'Salesforce (CRM)', 'SAP (SAP)', 'Siemens (SIE.DE)', 'ServiceNow (NOW)', 'Adobe (ADBE)', 'Oracle (ORCL)', 'Intuit (INTU)', 'Palo Alto Networks (PANW)', 'Snowflake (SNOW)'
    ]
})

# 既存のリストと結合（以前の global_stocks などと合わせてください）
df_csv = pd.concat([global_stocks, software_global_stocks, df_csv], ignore_index=True)

# 重複を排除して保存
df_csv = df_csv.drop_duplicates(subset=['code'])
df_csv.to_csv("jpx_stocks.csv", index=False)
print("✅ jpx_stocks.csv の作成が完了しました！")