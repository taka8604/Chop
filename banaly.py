import ccxt
import pandas as pd
import numpy as np
import requests
from google.colab import files

# Telegram gönderim fonksiyonu
def send_telegram_message(file_path, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    files = {'document': open(file_path, 'rb')}
    data = {'chat_id': chat_id}
    
    response = requests.post(url, data=data, files=files)
    if response.status_code == 200:
        print("Dosya başarıyla gönderildi.")
    else:
        print("Dosya gönderilemedi. Hata kodu:", response.status_code)

# OHLCV verilerini almak için fonksiyon
def fetch_ohlcv_data(exchange, symbol, timeframe, limit=None):
    try:
        ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Veri alınırken hata oluştu ({symbol} - {timeframe}): {e}")
        return None

# RMA (Eksponansiyel Hareketli Ortalama) fonksiyonu
def rma(series, length):
    return series.ewm(alpha=1/length, adjust=False).mean()

# True Range hesaplama fonksiyonu
def tr(data):
    data['previous_close'] = data['close'].shift(1)
    tr1 = abs(data['high'] - data['low'])
    tr2 = abs(data['high'] - data['previous_close'])
    tr3 = abs(data['low'] - data['previous_close'])
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

# Choppiness Index hesaplama fonksiyonu
def choppiness_index(data, length=14):
    atr_sum = data['high'].sub(data['low']).rolling(window=length).sum()
    highest_high = data['high'].rolling(window=length).max()
    lowest_low = data['low'].rolling(window=length).min()

    ci = 100 * np.log10(atr_sum / (highest_high - lowest_low)) / np.log10(length)
    return pd.Series(ci, name=f'CHOP_{length}')

# Directional Movement Index (DMI) ve ADX hesaplama fonksiyonu
def directional_movement_index(data, dilen=14, adxlen=14):
    up = data['high'].diff()
    down = -data['low'].diff()

    PositifDM = np.where((up > down) & (up > 0), up, 0)
    NegatifDM = np.where((down > up) & (down > 0), down, 0)

    trur = rma(tr(data), dilen)
    Positif = 100 * rma(pd.Series(PositifDM), dilen) / trur
    Negatif = 100 * rma(pd.Series(NegatifDM), dilen) / trur

    sum_ = Positif + Negatif
    adx = 100 * rma(abs(Positif - Negatif) / (sum_.replace(0, 1)), adxlen)

    return pd.DataFrame({'ADX': adx, 'Positif_DI': Positif, 'Negatif_DI': Negatif}, index=data.index)

# RSI hesaplama fonksiyonu
def rsi(data, period=14):
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi_value = 100 - (100 / (1 + rs))
    return rsi_value

# Pairs analiz fonksiyonu (CHOP değeri 61.8'den büyükse dahil et)
def analyze_pair(exchange, symbol, timeframes):
    pair_data = {'Sembol': symbol, 'Timeframes': []}
    for timeframe in timeframes:
        data = fetch_ohlcv_data(exchange, symbol, timeframe)

        # Veri boş mu diye kontrol et
        if data is not None and not data.empty:
            data['CHOP'] = choppiness_index(data, length=14)
            # Burada CHOP değerini 61.8'den büyükse filtreliyoruz
            if data['CHOP'].iloc[-1] > 61.8:
                dmi_data = directional_movement_index(data, dilen=14, adxlen=14)
                data = pd.concat([data, dmi_data], axis=1)
                data['Positif_Ustunde_Negatif'] = np.where(data['Positif_DI'] > data['Negatif_DI'], 'Ustunde', 'Altinda')

                # RSI hesaplama
                data['RSI'] = rsi(data, period=14)

                # Her bir göstergenin son değerini alırken NaN kontrolü yap
                pair_data[f'CHOP_{timeframe}'] = data['CHOP'].iloc[-1] if not data['CHOP'].isnull().iloc[-1] else np.nan
                pair_data[f'ADX_{timeframe}'] = data['ADX'].iloc[-1] if not data['ADX'].isnull().iloc[-1] else np.nan
                pair_data[f'Positif_DI_{timeframe}'] = data['Positif_DI'].iloc[-1] if not data['Positif_DI'].isnull().iloc[-1] else np.nan
                pair_data[f'Negatif_DI_{timeframe}'] = data['Negatif_DI'].iloc[-1] if not data['Negatif_DI'].isnull().iloc[-1] else np.nan
                pair_data[f'Positif_Ustunde_Negatif_{timeframe}'] = data['Positif_Ustunde_Negatif'].iloc[-1] if not data['Positif_Ustunde_Negatif'].isnull().iloc[-1] else "N/A"
                pair_data[f'RSI_{timeframe}'] = data['RSI'].iloc[-1] if not data['RSI'].isnull().iloc[-1] else np.nan
                pair_data['Timeframes'].append(timeframe)  # Eklenen zaman dilimlerini kaydet
        else:
            # Veri yoksa bir uyarı yazdır ve o timeframe için devam et
            print(f"Uyarı: {symbol} sembolü için {timeframe} zaman diliminde veri bulunamadı.")
            continue
    return pair_data

# Kombine analiz sonuçlarını txt dosyasına kaydetme
def save_results_to_txt(pairs, filename='binance_analysis_results.txt'):
    with open(filename, 'w') as f:
        f.write("Binance Farklı Zaman Dilimlerinde Çıkan Semboller:\n\n")

        # Farklı zaman dilimlerinde çıkan semboller sıralanır
        multi_timeframe_pairs = sorted(pairs, key=lambda x: len(x['Timeframes']), reverse=True)

        for pair in multi_timeframe_pairs:
            symbol = pair['Sembol']
            f.write(f"{symbol}\n")

            for timeframe in pair['Timeframes']:
                f.write(f"{timeframe} Chop: {pair.get(f'CHOP_{timeframe}', 'N/A')}\n")

            f.write("-" * 40 + "\n")

            for timeframe in pair['Timeframes']:
                f.write(f"{timeframe} ADX: {pair.get(f'ADX_{timeframe}', 'N/A')}\n")

            f.write("-" * 40 + "\n")

            for timeframe in pair['Timeframes']:
                f.write(f"{timeframe} Pozitif DMI: {pair.get(f'Positif_Ustunde_Negatif_{timeframe}', 'N/A')}\n")

            f.write("-" * 40 + "\n")

            for timeframe in pair['Timeframes']:
                f.write(f"{timeframe} RSI: {pair.get(f'RSI_{timeframe}', 'N/A')}\n")

            f.write("-" * 40 + "\n\n")

# Exchange bağlantısı oluşturma
exchange = ccxt.binance()

# Piyasaları yükleme
markets = exchange.load_markets()
usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT') and 'UP' not in symbol and 'DOWN' not in symbol]

# Zaman dilimleri
timeframes = ['1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']

# Pairs analizini yapma
analyzed_pairs = []
for symbol in usdt_pairs:
    pair_data = analyze_pair(exchange, symbol, timeframes)
    if pair_data and pair_data['Timeframes']:
        analyzed_pairs.append(pair_data)

# Sonuçları txt dosyasına kaydetme
txt_filename = 'binance_analysis_results.txt'
save_results_to_txt(analyzed_pairs, filename=txt_filename)

# Telegram botuyla txt dosyasını gönderme
API_TOKEN = '5141924896:AAGUMzfDSu1N9EXFQBiy7FBJTYah9Ej-9I8'
CHAT_ID = '@signalakin2023'

send_telegram_message(txt_filename, API_TOKEN, CHAT_ID)