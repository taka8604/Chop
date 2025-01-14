import requests
import time
import datetime
from collections import defaultdict

# Borsa ve coin bilgilerini belirleyin
API_URL = 'https://www.okx.com/api/v5/market/tickers'

# Sadece USDT pariteleri ve 50.000 USD üzeri alımlar için
ALIM_LIMIT = 50000  # Burada ALIM_LIMIT'i 50.000 USD olarak güncelledik

# Coin alımlarının günlük sayısını tutmak için bir sözlük
coin_count = defaultdict(int)

# Telegram bot bilgileri
bot_token = "5141924896:AAGUMzfDSu1N9EXFQBiy7FBJTYah9Ej-9I8"
channel_username = "@Whalealert1986"

# Telegram mesaj gönderme fonksiyonu
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        "chat_id": channel_username,
        "text": message,
        "parse_mode": "HTML"  # Mesajın formatı HTML olacak
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()  # Hata durumunda istisna fırlat
    except requests.exceptions.RequestException as e:
        print(f"Telegram mesaj gönderme hatası: {e}")

# Sayaç sıfırlama fonksiyonu (yeni gün başladığında)
def reset_count_if_new_day(last_reset_time):
    global coin_count
    current_time = time.time()
    # Geçerli saati Türkiye saatiyle karşılaştır (00:00:00'ı bekle)
    current_time_in_utc = datetime.datetime.utcfromtimestamp(current_time)
    current_time_in_tz = current_time_in_utc + datetime.timedelta(hours=3)  # Türkiye saati

    if current_time_in_tz.hour == 0 and current_time_in_tz.minute == 0 and current_time_in_tz.second == 0:
        # Yeni gün başladıysa sayaç sıfırlanacak
        print(f"Yeni gün başladı. Sayaç sıfırlanıyor...")

        # Coin bazında toplam sinyal sayısını Telegram'a gönder (sıralama yapıldı)
        message = "<b>OKX Günlük Toplam Sinyal Sayısı:</b>\n"

        # Sinyal sayısına göre azalan sırayla sıralama yap
        sorted_coin_count = sorted(coin_count.items(), key=lambda x: x[1], reverse=True)

        for pair, count in sorted_coin_count:
            message += f"{pair}: {count}\n"

        send_telegram_message(message)

        # Sayaç sıfırlanacak
        coin_count = defaultdict(int)
        return current_time, coin_count  # Sayaç sıfırlanacak ve son reset zamanı güncellenmiş olacak

    return last_reset_time, coin_count  # coin_count mevcut sayılarla döndürülür

# Büyük alımları kontrol eden fonksiyon
def display_large_buys():
    last_reset_time = time.time()

    print("Başlatılıyor... sadece $50.000 ve üzeri alımlar görünecek!")

    while True:
        try:
            # Piyasa verilerini al
            params = {'instType': 'SPOT'}  # instType parametresi "SPOT" olarak ekleniyor
            response = requests.get(API_URL, params=params)
            data = response.json()

            # Veriyi alabilip almadığımızı kontrol et
            if data['code'] != '0':
                continue

            # Coin/USDT paritelerini filtrele ve büyük alımları göster
            for market in data['data']:
                pair = market['instId']

                # Filtrelenecek pariteler: USDT-TRY, USDC-USDT, PYUSD-USDT, USDT-BRL, USDT-AED
                if 'USDT' not in pair or pair in ['USDT-TRY', 'USDC-USDT', 'PYUSD-USDT', 'USDT-BRL', 'USDT-AED']:
                    continue

                # Alım fiyatı, miktarı ve toplam değeri
                last_price = float(market['last'])
                last_size = float(market['lastSz'])
                total_value = last_price * last_size

                # Alım limiti kontrolü
                if total_value >= ALIM_LIMIT:
                    # Sadece 50.000 USD ve üzeri alımları yazdır
                    message = f"<b>50.000 dolar ve üzeri alım yapıldı.</b>\n"
                    message += f"<b>Borsa:</b> OKX\n"
                    message += f"<b>Coin:</b> {pair}\n"
                    message += f"<b>Alış Fiyatı:</b> {last_price:.4f} USD\n"
                    message += f"<b>Alış Miktarı:</b> {last_size:.8f}\n"
                    message += f"<b>Toplam Değer:</b> {total_value:,.6f} USD\n"

                    # Coin işlemi sayısını arttır
                    global coin_count  # Burada global anahtar kelimesi kullanıldı
                    coin_count[pair] += 1

                    # Günlük sinyal sayısı
                    message += f"<b>Günlük Sinyal Sayısı:</b> {coin_count[pair]}\n"

                    # Telegram'a mesaj gönder
                    send_telegram_message(message)

            # Sayaç sıfırlama kontrolü
            last_reset_time, coin_count = reset_count_if_new_day(last_reset_time)

            # 10 saniye bekle
            time.sleep(10)

        except Exception as e:
            print(f"Hata oluştu: {e}")
            time.sleep(10)

# Programı başlat
display_large_buys()