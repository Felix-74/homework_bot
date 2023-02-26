class BaseError(Exception):
    """Базовые исключения"""

    pass


class HTTPRequestError(Exception):
    """Базовые исключения."""

    def __init__(self, response):
        message = (
            f'Эндпоинт {response.url} недоступен. '
            f'Код ответа API: {response.status_code}]'
        )
        super().__init__(message)


class ResponseTypeError(BaseError):
    """Исключение возникает, когда тип ответа не соответствует документам."""

    pass


class APIRequestError(BaseError):
    """Исключение, возникающее, когда API возвращает неправильный ответ."""

    pass
