import logging
import json
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HTTPRequestError, ResponseTypeError, APIRequestError

load_dotenv()

logger = logging.getLogger(f'praktikum_{__name__}_bot')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s (%(name)s:%(lineno)d) [%(levelname)s]: %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


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
    """Проверяет доступность переменных окружения."""
    token_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    return all(token_list)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logger.debug(f'Отправляем сообщение {message}')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение {message}')
    except telegram.TelegramError:
        logger.error('Не удается отправить сообщение')


def get_api_answer(current_timestamp):
    """Создает и отправляет запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    params = {
        'from_date': timestamp
    }
    logger.info(f'Отправка запроса на {ENDPOINT} с параметрами {params}')
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.RequestException:
        raise APIRequestError(
            f'API error. Status code: {response.status_code}'
        )
    if response.status_code != HTTPStatus.OK:
        raise HTTPRequestError(response)
    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        raise ResponseTypeError('API response is of wrong type.')


def check_response(response):
    """Проверка полученного ответа от эндпоинта."""
    if not isinstance(response, dict):
        raise TypeError('response не является словарем')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        raise KeyError('Нет ключа "homeworks" в response')
    if 'current_date' not in response:
        raise KeyError('Нет ключа "current_date" в response')
    if not isinstance(homeworks, list):
        raise TypeError('"homeworks" не является списком')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа "homework_name" в homework')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Нет такого статуса')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_status = None

    def bot_send_check(message):
        if message != last_status:
                    return send_message(bot, message)
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        sys.exit(1)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                bot_send_check(message)
            else:
                logger.critical.debug('Ответ API пуст: нет домашних работ.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot_send_check(message)
        else:
            last_status = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
