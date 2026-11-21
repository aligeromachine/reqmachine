import requests

# ─────────────────────────── Исключения ───────────────────────────


class HttpClientError(Exception):
    """Базовая ошибка HTTP-клиента."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        url: str | None = None,
        response: requests.Response | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.url = url
        self.response = response


class HttpStatusError(HttpClientError):
    """Ответ получен, но код не 2xx/3xx."""


class HttpConnectionError(HttpClientError):
    """Не удалось установить соединение."""


class HttpTimeoutError(HttpClientError):
    """Таймаут соединения/чтения."""


class HttpDecodeError(HttpClientError):
    """Тело ответа не является валидным JSON."""
