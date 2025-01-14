import requests
import time
import datetime
from collections import defaultdict

# Binance API URL
API_URL_TICKER = 'https://api.binance.com/api/v3/exchangeInfo'
API_URL_DEPTH = 'https://api.binance.com/api/v3/depth'

# Alım limitleri (BTC paritesi için 500.000 USD, diğerleri için 300.000 USD)
ALIM_LIMIT_BTC = 500000
ALIM_LIMIT_OTHER = 300000

# Coin alımlarının günlük sayısını tutmak için bir sözlük
coin_count = defaultdict(int)

# Telegram bot bilgileri
bot_token = "5141924896:AAGUMzfDSu1N9EXFQBiy7FBJTYah9Ej-9I8"
channel_username = "@Whalealert1986"

# Tarama dışı pariteler (istenmeyen pariteler)
exclude_pairs = [
    "USDTTRY", "USDTBRL", "USDCUSDT", "USDTTBRL", "USDTARS", 
    "FDUSDUSDT", "FDUSDTRY", "USDTCOP", "USDTMXN"  # USDTMXN paritesi eklendi
]

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
        message = "<b>Binance Günlük Sinyal Sayısı:</b>\n"  # Başlık eklendi

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

    print("Başlatılıyor... BTC pariteleri için $500.000 ve üzeri alımlar, diğerleri için $300.000 ve üzeri alımlar görünecek!")

    while True:
        try:
            # Binance'ten tüm USDT paritelerini al
            response = requests.get(API_URL_TICKER)
            data = response.json()

            # Veriyi alabilip almadığımızı kontrol et
            if not data:
                continue

            # Tüm USDT paritelerini al, dışlanması gerekenleri filtrele
            usdt_pairs = [
                symbol['symbol'] for symbol in data['symbols'] 
                if 'USDT' in symbol['symbol'] and symbol['symbol'] not in exclude_pairs
            ]

            # Her bir parite için alış (bids) emirlerini kontrol et
            for pair in usdt_pairs:
                # Alım limitini belirle
                if 'BTC' in pair:
                    alım_limit = ALIM_LIMIT_BTC
                else:
                    alım_limit = ALIM_LIMIT_OTHER

                # Binance'ten her parite için derinlik (depth) verisini al
                response = requests.get(API_URL_DEPTH, params={'symbol': pair, 'limit': 5})
                depth_data = response.json()

                if not depth_data or 'bids' not in depth_data:
                    continue

                # Alış emirlerini (bids) kontrol et
                for order in depth_data['bids']:  # 'bids' kısmı alış (alım) emirlerini içerir
                    price = float(order[0])  # Fiyat
                    quantity = float(order[1])  # Miktar
                    total_value = price * quantity  # Alım emrinin toplam değeri

                    # Alım limiti kontrolü
                    if total_value >= alım_limit:
                        # Yalnızca belirlenen limitin üzerindeki alımları yazdır
                        message = f"<b>{alım_limit:,.0f} dolar ve üzeri alım yapıldı.</b>\n"
                        message += f"<b>Borsa:</b> Binance\n"  # Borsa bilgisini ekledik
                        message += f"<b>Coin:</b> {pair}\n"
                        message += f"<b>Alış Fiyatı:</b> {price:.4f} USD\n"
                        message += f"<b>Alış Miktarı:</b> {quantity:.8f}\n"
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