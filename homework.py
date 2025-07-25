import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='homework.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
stream_handler.setFormatter(formatter)
logging.getLogger().addHandler(stream_handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет наличие всех обязательных токенов."""
    if (
        PRACTICUM_TOKEN is None or
        TELEGRAM_TOKEN is None or
        TELEGRAM_CHAT_ID is None
    ):
        return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram и логирует результат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение успешно отправлено в Telegram')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения в Telegram: {error}')
        raise Exception(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Запрашивает данные у API Практикума и логирует ошибки доступа."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
        if response.status_code != 200:
            logging.error(f'Код ответа API: {response.status_code}')
            raise Exception(f'Код ответа API: {response.status_code}')
        return response.json()
    except requests.exceptions.ConnectionError as error:
        logging.error(f'Эндпоинт недоступен: {error}')
        raise Exception(f'Эндпоинт недоступен: {error}')
    except requests.exceptions.RequestException as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise Exception(f'Ошибка при запросе к API: {error}')


def check_response(response):
    """Проверяет корректность ответа API и логирует ошибки."""
    if not isinstance(response, dict):
        logging.error('Ответ API не является словарем')
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        logging.error('Отсутствует ключ "homeworks" в ответе API')
        raise KeyError('Отсутствует ключ "homeworks" в ответе API')
    if not isinstance(response['homeworks'], list):
        logging.error('Значение ключа "homeworks" не является списком')
        raise TypeError('Значение ключа "homeworks" не является списком')
    return response['homeworks']


def parse_status(homework):
    """Парсит статус домашней работы.

    Логирует неожиданные статусы.
    """
    if not isinstance(homework, dict):
        logging.error('Ответ API не является словарем')
        raise TypeError('Ответ API не является словарем')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status is None:
        logging.error('Отсутствуют обязательные ключи в ответе API')
        raise KeyError('Отсутствуют обязательные ключи в ответе API')
    if homework_status not in HOMEWORK_VERDICTS:
        logging.error(
            f'Неожиданный статус домашней работы: {homework_status}'
        )
        raise ValueError(
            f'Неожиданный статус домашней работы: {homework_status}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return (
        f'Изменился статус проверки работы "{homework_name}". {verdict}'
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствуют обязательные переменные окружения. Завершение работы.'
        )
        return
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error_message = None
    while True:
        try:
            response = get_api_answer({'from_date': timestamp})
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.debug('В ответе API нет новых статусов домашних работ')
            timestamp = response.get('current_date', timestamp)
            last_error_message = None
        except Exception as error:
            message = (
                f'Сбой в работе программы: {error}'
            )
            logging.error(message)
            if message != last_error_message:
                try:
                    send_message(bot, message)
                    last_error_message = message
                except Exception as send_error:
                    logging.error(
                        f'Не удалось отправить ошибку в Telegram: {send_error}'
                    )
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
