import logging
import os
import sys
import time
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import Any

import requests
import telegram
from dotenv import load_dotenv
from telegram.error import TelegramError

import user_exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_STATUSES = {
    'approved': "Работа проверена: ревьюеру всё понравилось. Ура!",
    'reviewing': "Работа взята на проверку ревьюером.",
    'rejected': "Работа проверена: у ревьюера есть замечания."
}


hw_logger = logging.getLogger(__name__)
hw_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
hw_logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)


def check_tokens() -> bool:
    """
    Проверка доступности переменных окружения.
    При успешной проверке возвращает True, в противном случае - False.
    """
    required_vars = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_vars = []
    for var in required_vars:
        if globals()[var] is None or globals()[var] == '':
            missing_vars.append(var)
    if missing_vars:
        hw_logger.critical(
            f"Отсутствуют необходимые переменные окружения: "
            f"{','.join(missing_vars)}.\n"
            f"Программа принудительно остановлена."
        )
        return False
    return True


def get_api_answer(current_timestamp: int) -> Any:
    """
    Делает запрос к эндпоинту API сервиса Практикум.Домашка и
    приводит данные ответа к формату Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.ConnectionError:
        raise requests.exceptions.ConnectionError(
            "Ошибка соединения с сервером API."
        )
    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout(
            "Ошибка ожидания ответа сервера API."
        )
    except requests.exceptions.TooManyRedirects:
        raise requests.exceptions.TooManyRedirects(
            "Превышен лимит переадресаций запроса к API по указанной ссылке."
        )
    except requests.exceptions.RequestException:
        raise requests.exceptions.RequestException(
            "Отказ в обслуживании запроса к API. "
        )
    if response.status_code != HTTPStatus.OK:
        raise user_exceptions.EndPointError
    try:
        response = response.json()
    except JSONDecodeError:
        raise JSONDecodeError("Ошибка декодирования ответа API.")
    return response


def check_response(response: Any) -> list:
    """
    Проверка ответа API на соотвествие ожидаемой структуре данных.
    При успешной проверке возвращает список домашних работ (может быть пустым).
    """
    if not isinstance(response, dict):
        raise TypeError("Ответ API не в виде словаря.")
    elif not response:
        raise user_exceptions.EmptyResponseDictError
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError("В ответе API отсутствует ключ 'homeworks'")
    elif not isinstance(homeworks, list):
        raise TypeError("Значение ключа 'homeworks' должно быть списком.'")
    return homeworks


def parse_status(homework: dict) -> str:
    """
    Извлекает статус домашней работы из словаря
    и возвращает сообщение соответствующее статусу.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError("В словаре 'homework' нет ключа 'homework_name'.")
    elif homework_status is None:
        raise KeyError("В словаре 'homework' нет ключа 'status'.")
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise user_exceptions.UnknownHomeworkStatusError
    return (f"Изменился статус проверки работы"
            f' "{homework_name}". {verdict}')


def send_message(bot: telegram.Bot, message: str) -> None:
    """
    Отправляет пользователю сообщение о статусе проверки домашней работы
    с помощью Telegram-бота.
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except TelegramError:
        raise TelegramError("Ошибка отправки сообщения в Telegram.")


def main() -> None:
    """Логика работы телеграм-бота."""
    if not check_tokens():
        raise user_exceptions.MissingVariableError
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    hw_logger.info("Бот запущен.")
    current_timestamp = int(time.time())
    previous_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
                    hw_logger.info(
                        f"Бот отправил сообщение:\n"
                        f"{message}"
                    )
            else:
                hw_logger.debug("Нет обновлений статуса домашних работ.")
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            hw_logger.error(error)
            if previous_error != error and not isinstance(
                error, TelegramError
            ):
                try:
                    send_message(bot, message)
                except TelegramError as t_error:
                    hw_logger.error(t_error)
            previous_error = error
        else:
            hw_logger.info(
                "Проверка статуса домашних работ успешно завершена."
            )
        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
