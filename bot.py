from telegram import Bot
from telegram.ext import Updater, CommandHandler
import subprocess

# Telegram bot bilgileri
bot_token = "5141924896:AAGUMzfDSu1N9EXFQBiy7FBJTYah9Ej-9I8"  # Botunuzun token'ı
channel_username = "@verikanali"  # Kanalınızın kullanıcı adı

# Komut geldiğinde çalışacak fonksiyon
def run_script(update, context):
    try:
        # İlk Python scriptini çalıştır (okxblow1w.py)
        result_okx = subprocess.run(['python3', '/root/okxblow1w.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output_okx = result_okx.stdout.decode('utf-8')
        error_okx = result_okx.stderr.decode('utf-8')

        # İkinci Python scriptini çalıştır (bnnceblow1w.py)
        result_bnnce = subprocess.run(['python3', '/root/bnnceblow1w.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output_bnnce = result_bnnce.stdout.decode('utf-8')
        error_bnnce = result_bnnce.stderr.decode('utf-8')

        # İlk scriptin çıktısını gönder
        if output_okx:
            context.bot.send_message(chat_id=channel_username, text=f"OKX Script Çıktısı:\n{output_okx}")
        elif error_okx:
            context.bot.send_message(chat_id=channel_username, text=f"OKX Hata:\n{error_okx}")

        # İkinci scriptin çıktısını gönder
        if output_bnnce:
            context.bot.send_message(chat_id=channel_username, text=f"BNNCE Script Çıktısı:\n{output_bnnce}")
        elif error_bnnce:
            context.bot.send_message(chat_id=channel_username, text=f"BNNCE Hata:\n{error_bnnce}")
        else:
            context.bot.send_message(chat_id=channel_username, text="Her iki scriptin de çıktısı boş.")
    except Exception as e:
        context.bot.send_message(chat_id=channel_username, text=f"Bir hata oluştu: {e}")

# Botu başlatan ana fonksiyon
def main():
    # Updater ile botu başlat
    updater = Updater(token=bot_token, use_context=True)
    dispatcher = updater.dispatcher

    # Komut handler'ı ekle
    dispatcher.add_handler(CommandHandler('run_script', run_script))

    # Polling ile çalışmaya başla
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()