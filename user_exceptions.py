'''
Файл с пользовательскими исключениями,
могут возникнуть при сбое работы пакета homework_bot.py .
'''

messages_dict = {
    'missing_var':
        "Отсутствуют необходимые переменные окружения.",
    'endpoint_error':
        ("Эндпоинт"
        " https://practicum.yandex.ru/api/user_api/homework_statuses/111"
        " недоступен. Код ответа API: 404"),
    'empty_response_dict':
        "Ответ API содержит пустой словарь.",
    'unknown_homework_status':
        "Недокументированный статус домашней работы.",
}


class MissingVariableError(Exception):
    """
    Ошибка отсутсвия переменной окружения.
    """
    def __init__(
        self, missing_vars, message=messages_dict['missing_var']
    ):
        self.missing_vars = missing_vars
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} {','.join(self.missing_vars)}"


class EndPointError(Exception):
    """
    Cбой запроса к эндпоинту API Практикум.Домашка.
    """
    def __init__(self, message=messages_dict['endpoint_error']):
        self.message = message
        super().__init__(self.message)


class EmptyResponseDictError(Exception):
    """
    Ошибка ответа API: ответ содержит пустой словарь.
    """
    def __init__(self, message=messages_dict['empty_response_dict']):
        self.message = message
        super().__init__(self.message)


class UnknownHomeworkStatusError(Exception):
    """
    Ошибка ответа API: ответ содержит неизвестный статус домашней работы.
    """
    def __init__(self, message=messages_dict['unknown_homework_status']):
        self.message = message
        super().__init__(self.message)
