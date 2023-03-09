import logging
import requests
import time

from http import HTTPStatus

import telegram
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = 280305615

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
timestamp = 1549962000

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    if (PRACTICUM_TOKEN is None
       or TELEGRAM_TOKEN is None
       or TELEGRAM_CHAT_ID is None):
        logger.critical('Недоступны переменные окружения')
        raise Exception


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(error)
    else:
        logger.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    try:
        payload = {'from_date': timestamp}
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
        response = homework_statuses.json()
        if homework_statuses.status_code != HTTPStatus.OK:
            message = 'API-сервис недоступен'
            raise Exception(message)
        return response
    except Exception:
        raise SystemError


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if not response:
        message = 'В ответе API пусто'
        raise Exception(message)
    if type(response) != dict:
        message = 'В ответе API передан не словарь'
        raise TypeError(message)
    if not isinstance(response.get('homeworks'), list):
        message = ('В ответе API под ключом homeworks данные '
                   'приходят не в виде списка')
        raise TypeError(message)


def parse_status(homework):
    """Статус работы.
    Извлекает из информации о конкретной
    домашней работе статус этой работы.
    """
    try:
        if 'homework_name' not in homework:
            raise Exception
        homework_name = homework.get('homework_name')
        verdict = homework.get('status')
        return (f'Изменился статус проверки работы "{homework_name}". '
                f'{HOMEWORK_VERDICTS[verdict]}')
    except KeyError:
        raise KeyError


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    prev_response = None

    while True:
        timestamp = 1549962000
        check = get_api_answer(timestamp)
        check_response(check)
        if len(check.get('homeworks')) == 0:
            logging.error('Список домшних заданий пуст')
            break
        check = check.get('homeworks')[0]
        new_response = parse_status(check)
        if prev_response != new_response:
            try:
                send_message(bot, new_response)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(message)

        prev_response = new_response
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
