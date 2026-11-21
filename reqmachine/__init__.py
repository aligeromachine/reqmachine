"""reqmachine — a small requests-based HTTP client.

Retries, JSON parsing (orjson), file upload/download helpers and
convenience decorators on top of :mod:`requests`.
"""

from .client import HttpClient, http_client, http_get, http_post
from .core.config import Config
from .core.types import JsonDict, JsonList, JsonValue, ResponseRequest
from .errors.errors import (
    HttpClientError,
    HttpConnectionError,
    HttpDecodeError,
    HttpStatusError,
    HttpTimeoutError,
)
from .validate.adapter import DictValidator, ListValidator

__version__ = "0.1.5"

__all__ = [
    "Config",
    "DictValidator",
    "HttpClient",
    "HttpClientError",
    "HttpConnectionError",
    "HttpDecodeError",
    "HttpStatusError",
    "HttpTimeoutError",
    "JsonDict",
    "JsonList",
    "JsonValue",
    "ListValidator",
    "ResponseRequest",
    "http_client",
    "http_get",
    "http_post",
]
