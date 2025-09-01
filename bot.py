import os
import sys
import logging
import tempfile
import base64
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import telebot
from google import genai

load_dotenv()

log_file = "bot.log"
max_bytes = 5 * 1024 * 1024
backup_count = 5

file_handler = RotatingFileHandler(
    log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s, %(levelname)s, %(message)s")
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, stream_handler])

GOOGLE_API_KEY = os.getenv("GOOGLE_API")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

client = genai.Client(api_key=GOOGLE_API_KEY)


def ask_gemini_text(prompt):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[{"text": prompt}]
        )
        return response.text
    except Exception as e:
        logging.error(f"Ошибка при запросе к Gemini API: {e}")
        return "Ошибка при запросе к модели Gemini."


def send_stub_message(chat_id, format_name):
    bot.send_message(
        chat_id,
        f"Я пока не умею обрабатывать {format_name}, закиньте денег на оплату ИИ и разработчик обязательно это добавит🙂",
    )


@bot.message_handler(commands=["start"])
def handle_start(message):
    welcome_text = (
        "Привет, я бот - нейросеть.\n"
        "Напиши мне что-нибудь, и я отвечу, наверное.\n"
        "А может и нет, хз."
    )
    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    send_stub_message(message.chat.id, "фотографии")


@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    send_stub_message(message.chat.id, "голосовые сообщения")


@bot.message_handler(content_types=["document"])
def handle_document(message):
    send_stub_message(message.chat.id, "документы")


@bot.message_handler(content_types=["location"])
def handle_location(message):
    send_stub_message(message.chat.id, "геолокации")


@bot.message_handler(content_types=["text"])
def handle_message(message):
    user_text = message.text.strip()
    if user_text.lower() == "дурила":
        bot.send_message(message.chat.id, "Сам ты дурила")
        return

    bot.send_chat_action(message.chat.id, "typing")
    response = ask_gemini_text(user_text)
    if not response:
        response = "Извините, не удалось получить ответ от нейросети."
    bot.send_message(message.chat.id, response)


def main():
    print("Бот запущен. Ожидание сообщений...")
    bot.infinity_polling()


if __name__ == "__main__":
    main()
