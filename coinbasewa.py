import requests
import time
import datetime
from collections import defaultdict

# Coinbase API URL
API_URL = 'https://api.coinbase.com/v2/exchange-rates'

# Sadece USDT pariteleri ve 100.000 USD üzeri alımlar için
ALIM_LIMIT = 100000

# Telegram bot bilgileri
bot_token = "5141924896:AAGUMzfDSu1N9EXFQBiy7FBJTYah9Ej-9I8"
channel_username = "@Whalealertcoinbase"  # Kanalınızın kullanıcı adı

# Coin alımlarının günlük sayısını tutmak için bir sözlük
coin_count = defaultdict(int)

# Filtrelenecek pariteler: USDT-TRY, USDC-USDT, PYUSD-USDT, USDT-AED, USDT-AUD, USDT-USDC, USDT-EUR, DAI-USDT, VEF, MOG
FILTERED_PAIRS = ['USDT-TRY', 'USDC-USDT', 'PYUSD-USDT', 'USDT-AED', 'USDT-AUD', 'USDT-USDC', 'USDT-EUR', 'DAI-USDT', 'VEF', 'MOG']

# Telegram'a mesaj göndermek için fonksiyon
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        "chat_id": channel_username,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Telegram mesaj hatası: {response.text}")
    except Exception as e:
        print(f"Hata oluştu: {e}")

# Sayaç sıfırlama fonksiyonu (yeni gün başladığında)
def reset_count_if_new_day(last_reset_time):
    global coin_count  # coin_count değişkenini global olarak tanımlıyoruz
    current_time = time.time()
    # Geçerli saati Türkiye saatiyle karşılaştır (00:00:00'ı bekle)
    current_time_in_utc = datetime.datetime.utcfromtimestamp(current_time)
    current_time_in_tz = current_time_in_utc + datetime.timedelta(hours=3)  # Türkiye saati

    if current_time_in_tz.hour == 0 and current_time_in_tz.minute == 0 and current_time_in_tz.second == 0:
        # Yeni gün başladıysa sayaç sıfırlanacak
        print(f"Yeni gün başladı. Sayaç sıfırlanıyor...")  # Bu satır terminaldeki bilgilendirmedir, isteğe göre kaldırılabilir.
        coin_count = defaultdict(int)  # Sayaç sıfırlanacak
        return current_time, coin_count  # Sayaç sıfırlanacak ve son reset zamanı güncellenmiş olacak
    return last_reset_time, coin_count  # coin_count mevcut sayılarla döndürülür

# Coinbase API'sinden alımları kontrol eden fonksiyon
def display_large_buys():
    global coin_count  # coin_count değişkenini global olarak tanımlıyoruz
    last_reset_time = time.time()

    while True:
        try:
            # Coinbase API'sinden veriyi al
            response = requests.get(API_URL)
            data = response.json()

            # Veriyi alabilip almadığımızı kontrol et
            if response.status_code != 200:
                print(f"Error fetching pairs: {data}")
                continue

            # USDT pariteleri için fiyat bilgisi kontrolü
            if 'data' in data and 'rates' in data['data']:
                rates = data['data']['rates']

                # Filtrelenecek paritelerden herhangi biri varsa devam etme
                for pair, rate in rates.items():
                    if pair in FILTERED_PAIRS:
                        continue

                    # Alım fiyatı ve toplam değeri kontrol et
                    last_price = float(rate)  # Son işlem fiyatı
                    total_value = last_price  # Bu örnekte sadece fiyat üzerinden işlem yapılacak

                    # Alım limiti kontrolü
                    if total_value >= ALIM_LIMIT:
                        # Sadece 100.000 USD ve üzeri alımları Telegram'a gönder
                        message = f"""
*100.000 dolar ve üzeri alım yapıldı.*
*Borsa:* Coinbase
*Coin:* {pair}
*Alış Fiyatı:* {last_price:.4f} USD
*Toplam Değer:* {total_value:,.6f} USD
*Günlük Sinyal Sayısı:* {coin_count[pair]}
"""
                        send_telegram_message(message)

                        # Coin işlemi sayısını arttır
                        coin_count[pair] += 1

            # Sayaç sıfırlama kontrolü
            last_reset_time, coin_count = reset_count_if_new_day(last_reset_time)

            # 10 saniye bekle
            time.sleep(10)

        except Exception as e:
            print(f"Hata oluştu: {e}")
            time.sleep(10)

# Programı başlat
display_large_buys()