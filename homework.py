import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (ListKeyError, NoResponseError, NotaListError,
                        ParseMissStatusError, SendMessageError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s -'
                              ' %(levelname)s - %(message)s')
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляем сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение отправлено: {message}')
    except Exception as error:
        raise SendMessageError(f'Сообщение не отправлено: {message} \n'
                               f'Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Запрос к API yandex."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    request_dict = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params}
    response = requests.get(
        **request_dict)
    if response.status_code != HTTPStatus.OK:
        raise NoResponseError(f'Нет ответа от: {ENDPOINT} .'
                              f'Статус код: {response.status_code}')
    response = response.json()
    logger.debug(f' Ответ от API: {response}')
    return response


def check_response(response):
    """Ответ API проверяется на корректность."""
    list_homeworks = response['homeworks']
    if not isinstance(list_homeworks, list):
        raise NotaListError(f'{list_homeworks} не является списком')
    if list_homeworks is None:
        raise ListKeyError(f'Неверный ключ для списка: {list_homeworks}')
    logger.debug(list_homeworks)
    return list_homeworks


def parse_status(homework):
    """Проверяем статус домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        logger.debug(verdict)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise ParseMissStatusError(
        f'Статус домашней работы : {homework_status}'
        f'Отсутствует в списке статусов: {HOMEWORK_STATUSES}')


def check_tokens():
    """Проверяется наличие необходимых переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens:
        logger.critical('Отсутствуют переменные окружения в файле .env')
        sys.exit('Проверьте наличие переменных в файле .env')

    cached_response = None
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if cached_response != response.get('homeworks'):
                cached_response = response.get('homeworks')
                homework = check_response(response)
                if homework:
                    homework_verdict = parse_status(homework[0])
                    send_message(bot, homework_verdict)
            else:
                logger.debug('В ответе от API отсутствуют новые статусы.')

        except SendMessageError as error:
            logger.error(error)

        except Exception as error:
            logger.error(error)
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
