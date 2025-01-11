import ccxt
import pandas as pd
import numpy as np

# Binance borsası API bağlantısı
exchange = ccxt.binance()

# 1 haftalık (7 günlük) verileri çekmek için
timeframe = '1w'
limit = 100  # En fazla 100 veri noktası alabiliriz

# USDT paritelerinin listesini almak
markets = exchange.load_markets()
usdt_pairs = [symbol for symbol in markets if 'USDT' in symbol]

# WaveTrend hesaplaması
def calculate_wavetrend(data, n1=10, n2=21):
    hlc3 = (data['high'] + data['low'] + data['close']) / 3
    esa = hlc3.ewm(span=n1).mean()
    d = (abs(hlc3 - esa)).ewm(span=n1).mean()
    ci = (hlc3 - esa) / (0.015 * d)
    tci = ci.ewm(span=n2).mean()
    
    wt1 = tci
    wt2 = wt1.rolling(window=4).mean()
    
    return wt1, wt2

# MACD hesaplaması
def calculate_macd(data, fast=12, slow=26, signal=9):
    # Kısa ve uzun vadeli EMA'lar
    macd_line = data['close'].ewm(span=fast, adjust=False).mean() - data['close'].ewm(span=slow, adjust=False).mean()
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, macd_signal

# Chop İndikatörü hesaplaması (Doğru versiyon)
def calculate_chop(data, n=14):
    # Gerçek Aralık (True Range) hesaplama
    tr = pd.DataFrame({
        'high-low': data['high'] - data['low'],
        'high-prev_close': abs(data['high'] - data['close'].shift(1)),
        'low-prev_close': abs(data['low'] - data['close'].shift(1)),
    })
    tr = tr.max(axis=1)  # En büyük değeri al
    tr_sum = tr.rolling(window=n).sum()  # Toplam True Range
    
    # Range hesaplama: en yüksek fiyat ile en düşük fiyat arasındaki fark
    highest_high = data['high'].rolling(window=n).max()
    lowest_low = data['low'].rolling(window=n).min()
    range_ = highest_high - lowest_low
    
    # Chop İndikatörü hesaplama
    ci = 100 * np.log10(tr_sum / range_) / np.log10(n)
    return ci

# Sonuçları tutacak bir liste
results = set()  # set kullanarak tekrarları engelleyeceğiz

# Tüm USDT paritelerini taramak
for pair in usdt_pairs:
    print(f"Processing {pair}...")
    try:
        # Geçersiz pariteleri atlama (USDT:USDT gibi)
        if 'USDT:USDT' in pair:
            continue
        
        # Verileri çekme
        ohlcv = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
        
        # Veriyi DataFrame'e çevirme
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # WaveTrend hesaplamaları
        wt1, wt2 = calculate_wavetrend(df)
        
        # MACD hesaplamaları
        macd_line, macd_signal = calculate_macd(df)
        
        # Chop indikatörü hesaplama
        chop_index = calculate_chop(df)
        
        # Son `wt1`, `wt2`, `macd_line`, `macd_signal` ve Chop indeksini kontrol etme
        if (wt1.iloc[-1] < 0 and wt2.iloc[-1] < 0 and 
            macd_line.iloc[-1] < 0 and macd_signal.iloc[-1] < 0 and
            chop_index.iloc[-1] >= 61.78):
            results.add(pair)  # set kullanıldığı için tekrarlar engellenir
        
    except Exception as e:
        print(f"Error processing {pair}: {e}")

# Sonuçları yazdırma
if results:
    print("Pairs with wt1, wt2, macd_line, macd_signal below 0 and chop index >= 61.78:")
    for result in results:
        print(result)
else:
    print("No pairs found with wt1, wt2, macd_line, macd_signal below 0 and chop index >= 61.78.")