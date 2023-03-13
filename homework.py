import logging
import requests
import time

from http import HTTPStatus

import telegram
import os

from dotenv import load_dotenv

from exceptions import APIError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
timestamp = 0

ERROR_CHECK_TOKENS = 'Недоступна переменная окружения {}'
DEBUG_SEND_MESSAGE = 'Сообщение отправлено'
ERROR_SEND_MESSAGE = 'Сообщение не отправлено'
API_NOT_AVAILABLE_GET_API_ANSWER = 'API-сервис недоступен'
JSON_ERROR_GET_API_ANSWER = 'Ошибка преобразования ответа в JSON'
REQUEST_API_GET_API_ANSWER = 'Произошла ошибка при выполнении запроса API: {}'
EMPTY_API_CHECK_RESPONSE = 'В ответе API пусто'
TYPEERROR_CHECK_RESPONSE = 'В ответе API передан не словарь'
HOMEWORKS_TYPE_ERROR_CHECK_RESPONSE = ('В ответе API под ключом homeworks '
                                       'данные приходят не в виде списка')
STATUS_PARSE_STATUS = 'Изменился статус проверки работы "{}". {}'
KEYERROR_PARSE_STATUS = 'Ключа {} не существует'
EMPTY_MAIN = 'Список домшних заданий пуст'
ERROR_MAIN = 'Сбой в работе программы: {}'

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    enviroments = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for name, value in enviroments.items():
        if value is None:
            message = ERROR_CHECK_TOKENS
            logger.critical(message.format(name))
            raise Exception(message.format(name))


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(DEBUG_SEND_MESSAGE)
    except Exception:
        logger.error(ERROR_SEND_MESSAGE)


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        response = homework_statuses.json()
        if homework_statuses.status_code != HTTPStatus.OK:
            logger.error(API_NOT_AVAILABLE_GET_API_ANSWER)
            raise Exception(API_NOT_AVAILABLE_GET_API_ANSWER)
        return response
    except ValueError:
        logger.error(JSON_ERROR_GET_API_ANSWER)
        raise Exception(JSON_ERROR_GET_API_ANSWER)
    except requests.RequestException as e:
        logger.error(REQUEST_API_GET_API_ANSWER)
        raise Exception(REQUEST_API_GET_API_ANSWER.format(e))


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if not response:
        logger.error(EMPTY_API_CHECK_RESPONSE)
        raise Exception(EMPTY_API_CHECK_RESPONSE)
    if not isinstance(response, dict):
        logger.error(TYPEERROR_CHECK_RESPONSE)
        raise TypeError(TYPEERROR_CHECK_RESPONSE)
    if not isinstance(response.get('homeworks'), list):
        logger.error(HOMEWORKS_TYPE_ERROR_CHECK_RESPONSE)
        raise TypeError(HOMEWORKS_TYPE_ERROR_CHECK_RESPONSE)


def parse_status(homework):
    """Статус работы.
    Извлекает из информации о конкретной
    домашней работе статус этой работы.
    """
    try:
        if 'homework_name' not in homework:
            logger.error(KEYERROR_PARSE_STATUS.format('homework_name'))
            raise KeyError(KEYERROR_PARSE_STATUS.format('homework_name'))
        homework_name = homework.get('homework_name')
        verdict = homework.get('status')
        return STATUS_PARSE_STATUS.format(
            homework_name, HOMEWORK_VERDICTS[verdict]
        )
    except Exception:
        logger.error(APIError.__doc__)
        raise APIError(APIError.__doc__)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    prev_response = None
    timestamp = int(time.time())
    while True:
        response = get_api_answer(timestamp)
        if len(response.get('homeworks')) == 0:
            logger.error(EMPTY_MAIN)
            break
        response_homework = response.get('homeworks')[0]
        new_response = parse_status(response_homework)
        if prev_response != new_response:
            try:
                check_tokens()
                check_response(response)
                send_message(bot, new_response)
            except Exception as error:
                logger.error(ERROR_MAIN.format(error))
        timestamp = int(time.time())
        prev_response = new_response
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s - %(funcName)s - %(levelname)s'
                ' - %(lineno)d - %(message)s'),
        level=logging.INFO,
        handlers=[
            logging.FileHandler(
                os.path.join(os.path.dirname(__file__), 'main.log')
            ),
            logging.StreamHandler(),
        ]
    )

    main()
