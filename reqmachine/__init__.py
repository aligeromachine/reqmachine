"""reqmachine — a small requests-based HTTP client.

Retries, JSON parsing (msgspec), typed response validation, file
upload/download helpers and convenience decorators on top of
:mod:`requests`.
"""

import importlib.metadata

from .client import HttpClient, http_client, http_get, http_post
from .core.config import Config
from .core.types import JsonDict, JsonList, JsonValue, ResponseRequest
from .errors.errors import (
    HttpClientError,
    HttpConnectionError,
    HttpDecodeError,
    HttpStatusError,
    HttpTimeoutError,
    HttpValidationError,
)
from .validate.adapter import JsonValidator

try:
    __version__ = importlib.metadata.version("reqmachine")
except importlib.metadata.PackageNotFoundError:  # запуск из репозитория без установки
    __version__ = "0.0.0+unknown"

__all__ = [
    "Config",
    "HttpClient",
    "HttpClientError",
    "HttpConnectionError",
    "HttpDecodeError",
    "HttpStatusError",
    "HttpTimeoutError",
    "HttpValidationError",
    "JsonDict",
    "JsonList",
    "JsonValidator",
    "JsonValue",
    "ResponseRequest",
    "http_client",
    "http_get",
    "http_post",
]
