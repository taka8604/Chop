import ccxt
import pandas as pd
import numpy as np
import asyncio
from telegram import Bot
from telegram.ext import Application

# Telegram bot token'ınızı buraya girin
API_TOKEN = '5141924896:AAGUMzfDSu1N9EXFQBiy7FBJTYah9Ej-9I8'
# Telegram'dan botunuzun mesaj göndereceği chat ID (bunu bir kullanıcıyla chat yaparak öğrenebilirsiniz)
CHAT_ID = '@signalakin2023'

# Botu başlatıyoruz
application = Application.builder().token(API_TOKEN).build()

# Mesaj gönderme fonksiyonu (asenkron)
async def send_telegram_message(message):
    try:
        await application.bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print(f"Error sending message: {e}")

# Mesajı uzunluk sınırına göre parçalara bölecek fonksiyon
def split_message(message, max_length=4096):
    # Telegram mesaj boyutunu aşarsa, mesajı parçalara ayırıyoruz
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

# Analiz sonuçlarını formatlayarak mesaj gönderecek fonksiyon
def format_pairs_for_telegram(pairs, timeframe):
    message = f"\nChoppiness Index greater than 61.78 in {timeframe} timeframe:\n"
    for pair in pairs:
        message += f"Sembol: {pair['Sembol']}\n"
        message += f"  CHOP_{timeframe}: {pair[f'CHOP_{timeframe}']:.2f}\n"
        message += f"  ADX_{timeframe}: {pair[f'ADX_{timeframe}']:.2f}\n"
        message += f"  Positif_DI_{timeframe}: {pair[f'Positif_DI_{timeframe}']:.2f}\n"
        message += f"  Negatif_DI_{timeframe}: {pair[f'Negatif_DI_{timeframe}']:.2f}\n"
        message += f"  Positif_Ustunde_Negatif_{timeframe}: {pair[f'Positif_Ustunde_Negatif_{timeframe}']}\n\n"
    return message

# Telegram'a veri gönderme (asenkron)
async def send_analysis_to_telegram():
    # Veriyi her bir zaman dilimi için tek tek göndereceğiz

    timeframes = ['1h', '4h', '1d', '3d', '1w']
    pairs_by_timeframe = {
        '1h': pairs_Ustunde_61_8_1h,
        '4h': pairs_Ustunde_61_8_4h,
        '1d': pairs_Ustunde_61_8_1d,
        '3d': pairs_Ustunde_61_8_3d,
        '1w': pairs_Ustunde_61_8_1w
    }

    for timeframe in timeframes:
        pairs = pairs_by_timeframe.get(timeframe, [])
        if pairs:
            message = format_pairs_for_telegram(pairs, timeframe)
            # Mesajı parçalara böl
            parts = split_message(message)
            for part in parts:
                await send_telegram_message(part)
        else:
            print(f"No pairs for {timeframe}.")

# Başka fonksiyonlar burada...

def fetch_ohlcv_data(exchange, symbol, timeframe, limit=None):
    try:
        ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol} ({timeframe}): {e}")
        return None

def rma(series, length):
    return series.ewm(alpha=1/length, adjust=False).mean()

def tr(data):
    data['previous_close'] = data['close'].shift(1)
    tr1 = abs(data['high'] - data['low'])
    tr2 = abs(data['high'] - data['previous_close'])
    tr3 = abs(data['low'] - data['previous_close'])
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def choppiness_index(data, length=14):
    atr_sum = data['high'].sub(data['low']).rolling(window=length).sum()
    highest_high = data['high'].rolling(window=length).max()
    lowest_low = data['low'].rolling(window=length).min()

    ci = 100 * np.log10(atr_sum / (highest_high - lowest_low)) / np.log10(length)
    return pd.Series(ci, name=f'CHOP_{length}')

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

def analyze_pair(exchange, symbol, timeframes):
    pair_data = {'Sembol': symbol}
    for timeframe in timeframes:
        data = fetch_ohlcv_data(exchange, symbol, timeframe)
        if data is not None:
            data['CHOP'] = choppiness_index(data, length=14)
            dmi_data = directional_movement_index(data, dilen=14, adxlen=14)
            data = pd.concat([data, dmi_data], axis=1)
            data['Positif_Ustunde_Negatif'] = np.where(data['Positif_DI'] > data['Negatif_DI'], 'Ustunde', 'Altında')

            pair_data[f'CHOP_{timeframe}'] = data['CHOP'].iloc[-1]
            pair_data[f'ADX_{timeframe}'] = data['ADX'].iloc[-1]
            pair_data[f'Positif_DI_{timeframe}'] = data['Positif_DI'].iloc[-1]
            pair_data[f'Negatif_DI_{timeframe}'] = data['Negatif_DI'].iloc[-1]
            pair_data[f'Positif_Ustunde_Negatif_{timeframe}'] = data['Positif_Ustunde_Negatif'].iloc[-1]
        else:
            continue
    return pair_data

# Initialize exchange connection
exchange = ccxt.binance()

# Load market pairs
markets = exchange.load_markets()
usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT')]

# Timeframes for analysis
timeframes = ['1h', '4h', '1d', '3d', '1w']

# Analyze all pairs
analyzed_pairs = []
for symbol in usdt_pairs:
    pair_data = analyze_pair(exchange, symbol, timeframes)
    if pair_data:
        analyzed_pairs.append(pair_data)

# Filter pairs based on CHOP value (greater than 60) for each timeframe
pairs_Ustunde_61_8_1h = [pair for pair in analyzed_pairs if pair.get('CHOP_1h', 0) > 60]
pairs_Ustunde_61_8_4h = [pair for pair in analyzed_pairs if pair.get('CHOP_4h', 0) > 60]
pairs_Ustunde_61_8_1d = [pair for pair in analyzed_pairs if pair.get('CHOP_1d', 0) > 60]
pairs_Ustunde_61_8_3d = [pair for pair in analyzed_pairs if pair.get('CHOP_3d', 0) > 60]
pairs_Ustunde_61_8_1w = [pair for pair in analyzed_pairs if pair.get('CHOP_1w', 0) > 60]

# Sort pairs by CHOP value for each timeframe
pairs_Ustunde_61_8_1h.sort(key=lambda x: x.get('CHOP_1h', 0), reverse=True)
pairs_Ustunde_61_8_4h.sort(key=lambda x: x.get('CHOP_4h', 0), reverse=True)
pairs_Ustunde_61_8_1d.sort(key=lambda x: x.get('CHOP_1d', 0), reverse=True)
pairs_Ustunde_61_8_3d.sort(key=lambda x: x.get('CHOP_3d', 0), reverse=True)
pairs_Ustunde_61_8_1w.sort(key=lambda x: x.get('CHOP_1w', 0), reverse=True)

# Asenkron işlemi mevcut event loop içinde başlatıyoruz
# Eğer asyncio.run() kullanıyorsanız, şu şekilde çağırabilirsiniz:
if __name__ == "__main__":
    asyncio.create_task(send_analysis_to_telegram())  # Bu satır mevcut event loop içinde çalışacaktır.