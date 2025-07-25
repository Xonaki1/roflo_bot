import requests
import json
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import telebot

load_dotenv()

log_file = 'bot.log'
max_bytes = 5 * 1024 * 1024
backup_count = 5

file_handler = RotatingFileHandler(
    log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, stream_handler]
)

API_KEY = os.getenv('OPEN_ROUTER')
MODEL = "deepseek/deepseek-chat-v3-0324:free"
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = telebot.TeleBot(TELEGRAM_TOKEN)


def process_content(content):
    """Удаляет теги <think> и </think> из строки."""
    return content.replace('<think>', '').replace('</think>', '')


def ask_neuro(prompt):
    """Отправляет запрос к OpenRouter и возвращает полный ответ нейросети."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Отвечай всегда на русском языке."},
            {"role": "user", "content": prompt}
        ],
        "stream": True
    }
    try:
        with requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            stream=True,
            timeout=60
        ) as response:
            if response.status_code != 200:
                logging.error(f"Ошибка API: {response.status_code}")
                return f"Ошибка API: {response.status_code}"
            full_response = []
            for chunk in response.iter_lines():
                if not chunk:
                    continue
                chunk_str = chunk.decode('utf-8').replace('data: ', '')
                if not chunk_str.strip():
                    continue  # пропускаем пустые строки
                try:
                    chunk_json = json.loads(chunk_str)
                    if "choices" in chunk_json:
                        content = chunk_json["choices"][0]["delta"].get("content", "")
                        if content:
                            cleaned = process_content(content)
                            full_response.append(cleaned)
                except Exception as e:
                    logging.debug(f"Ошибка парсинга чанка: {e} | chunk: {chunk_str}")
                    pass
            return ''.join(full_response)
    except requests.exceptions.Timeout:
        logging.error("Таймаут ожидания ответа от OpenRouter API")
        return "Время ожидания ответа от нейросети истекло. Попробуйте позже."
    except Exception as e:
        logging.error(f"Ошибка при запросе к API: {e}")
        return "Ошибка при запросе к API. Попробуйте позже."


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Приветствует пользователя при команде /start."""
    welcome_text = (
        "Привет, я бот - нейросеть.\n"
        "Напиши мне что-нибудь, и я отвечу, наверное.\n"
        "А может и нет, хз."
    )
    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(content_types=['text'])
def handle_message(message):
    """Обрабатывает входящее текстовое сообщение от пользователя Telegram."""
    user_text = message.text
    if user_text.strip().lower() == 'дурила':
        bot.send_message(message.chat.id, 'Сам ты дурила')
        return
    if user_text.strip().lower() == 'юна':
        bot.send_message(
            message.chat.id,
            'О Юна - повелитель нейросетей, приветствую тебя!'
        )
        return
    bot.send_chat_action(message.chat.id, 'typing')
    response = ask_neuro(user_text)
    if not response:
        response = "Извините, не удалось получить ответ от нейросети."
    bot.send_message(message.chat.id, response)


def main():
    """Запуск Telegram-бота."""
    print("Бот запущен. Ожидание сообщений...")
    bot.infinity_polling()


if __name__ == "__main__":
    main()
