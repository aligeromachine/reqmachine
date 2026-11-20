"""reqmachine — a small requests-based HTTP client.

Retries, JSON parsing (orjson), file upload/download helpers and
convenience decorators on top of :mod:`requests`.
"""

from .client import HttpClient, http_client, http_get, http_post
from .src.config import Config
from .src.errors import (
    HttpClientError,
    HttpConnectionError,
    HttpDecodeError,
    HttpStatusError,
    HttpTimeoutError,
)
from .src.types import JsonDict, JsonList, JsonValue

__version__ = "0.1.0"

__all__ = [
    "Config",
    "HttpClient",
    "HttpClientError",
    "HttpConnectionError",
    "HttpDecodeError",
    "HttpStatusError",
    "HttpTimeoutError",
    "JsonDict",
    "JsonList",
    "JsonValue",
    "http_client",
    "http_get",
    "http_post",
]
