from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, Concatenate, Self

import msgspec
import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    ConnectionError as ReqConnectionError,
)
from requests.exceptions import (
    HTTPError,
    RequestException,
)
from requests.exceptions import (
    Timeout as ReqTimeout,
)
from urllib3.util.retry import Retry

from reqmachine.validate.adapter import DictValidator, ListValidator

from .core.config import Config
from .errors.errors import (
    HttpClientError,
    HttpConnectionError,
    HttpDecodeError,
    HttpStatusError,
    HttpTimeoutError,
)

# ─────────────────────────── Клиент ───────────────────────────


class HttpClient:
    def __init__(
        self,
        *,
        verify: bool = False,
        timeout: tuple[float, float] = Config.API_TIMEOUT,
        upload_timeout: tuple[float, float] = Config.API_UPLOAD_TIMEOUT,
        headers: dict[str, str] | None = None,
        retries: int = Config.RETRY_TOTAL,
    ) -> None:
        self.timeout = timeout
        self.upload_timeout = upload_timeout
        self.chunk_size = Config.CHUNK_SIZE

        self.session = requests.Session()
        self.session.headers.update(Config.API_HEADERS)
        if headers:
            self.session.headers.update(headers)
        self.session.verify = verify

        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        retry = Retry(
            total=retries,
            backoff_factor=Config.RETRY_BACKOFF,
            status_forcelist=tuple(Config.RETRY_STATUSES),
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            raise_on_status=False,  # пусть raise_for_status сработает у нас
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ─── Жизненный цикл ───

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        self.session.close()

    # ─── Парсинг ───

    def _parse(self, response: requests.Response) -> dict | list | bytes | None:
        if not response.content:
            return None

        ctype = response.headers.get("Content-Type", "").lower()
        head = response.content[:1]
        looks_json = head in (b"{", b"[") or "json" in ctype

        if not looks_json:
            return response.content

        try:
            # msgspec.json.decode принимает bytes и возвращает dict/list
            return msgspec.json.decode(response.content)
        except msgspec.DecodeError as exc:
            raise HttpDecodeError(
                f"Invalid JSON from {response.url}: {exc}",
                url=response.url,
                response=response,
            ) from exc

    # ─── Валидация ───

    def _validate[T](
        self, response: dict | list | bytes | None, Model: type[T]
    ) -> T | list[T] | bytes | None:
        if not response:
            return None

        if isinstance(response, dict):
            validate_dict = DictValidator(Model)
            return validate_dict(response)

        if isinstance(response, list):
            validate_list = ListValidator(Model)
            return validate_list(response)

        return response

    # ─── Низкоуровневый запрос ───

    def _request[T](
        self, method: str, url: str, Model: type[T], **kwargs: Any
    ) -> T | list[T] | bytes | None:
        if kwargs.get("stream"):
            raise ValueError(
                "stream=True is not supported here; "
                "use download_file() or access self.session directly"
            )

        kwargs.setdefault("timeout", self.timeout)

        try:
            rsp = self.session.request(method, url, **kwargs)
            rsp.raise_for_status()
        except HTTPError as exc:
            r = exc.response
            status = r.status_code if r is not None else None
            raise HttpStatusError(
                f"HTTP {method} {url} -> {status}",
                status=status,
                url=url,
                response=r,
            ) from exc
        except ReqTimeout as exc:
            raise HttpTimeoutError(f"Timeout {method} {url}: {exc}", url=url) from exc
        except ReqConnectionError as exc:
            raise HttpConnectionError(
                f"Connection error {method} {url}: {exc}", url=url
            ) from exc
        except RequestException as exc:
            raise HttpClientError(
                f"Request failed {method} {url}: {exc}", url=url
            ) from exc

        response = self._parse(rsp)

        return self._validate(response=response, Model=Model)

    # ─── HTTP-методы ───

    def get[T](
        self,
        url: str,
        Model: type[T],
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> T | list[T] | bytes | None:
        return self._request("GET", url, Model=Model, params=params, **kwargs)

    def post[T](
        self,
        url: str,
        Model: type[T],
        *,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        **kwargs: Any,
    ) -> T | list[T] | bytes | None:
        if json is not None and data is not None:
            raise ValueError("Pass either json= or data=, not both")
        return self._request(
            "POST", url, Model=Model, json=json, data=data, files=files, **kwargs
        )

    def put[T](
        self,
        url: str,
        Model: type[T],
        *,
        json: Any = None,
        data: Any = None,
        **kwargs: Any,
    ) -> T | list[T] | bytes | None:
        if json is not None and data is not None:
            raise ValueError("Pass either json= or data=, not both")
        return self._request("PUT", url, Model=Model, json=json, data=data, **kwargs)

    def patch[T](
        self,
        url: str,
        Model: type[T],
        *,
        json: Any = None,
        data: Any = None,
        **kwargs: Any,
    ) -> T | list[T] | bytes | None:
        if json is not None and data is not None:
            raise ValueError("Pass either json= or data=, not both")
        return self._request("PATCH", url, Model=Model, json=json, data=data, **kwargs)

    def delete[T](
        self, url: str, Model: type[T], **kwargs: Any
    ) -> T | list[T] | bytes | None:
        return self._request("DELETE", url, Model=Model, **kwargs)

    # ─── Проверка доступности ───

    def is_url_available(self, url: str) -> bool:
        try:
            rsp = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            # Некоторые сервера отдают 405 на HEAD — пробуем GET
            if rsp.status_code == 405:
                rsp = self.session.get(
                    url, timeout=self.timeout, allow_redirects=True, stream=True
                )
                rsp.close()
            return 200 <= rsp.status_code < 400
        except RequestException:
            # Это проверка доступности, а не запрос данных: любая
            # сетевая ошибка означает "недоступен", без исключения.
            return False

    # ─── Файлы ───

    def upload_file(
        self,
        url: str,
        filein: Path,
        key: str | None = None,
        meta: dict | None = None,
    ) -> bool:
        """Загружает файл. Бросает HttpClientError при ошибке."""
        try:
            with filein.open("rb") as fr:
                files = {"file": (filein.name, fr, "application/octet-stream")}
                data = {key: msgspec.json.encode(meta)} if key else None
                rsp = self.session.post(
                    url,
                    files=files,
                    data=data,
                    timeout=self.upload_timeout,
                )
            rsp.raise_for_status()
        except HTTPError as exc:
            r = exc.response
            raise HttpStatusError(
                f"Upload failed {filein.name} -> {url}: "
                f"{r.status_code if r is not None else '?'}",
                status=r.status_code if r is not None else None,
                url=url,
                response=r,
            ) from exc
        except ReqTimeout as exc:
            raise HttpTimeoutError(
                f"Upload timed out {filein.name} -> {url}: {exc}", url=url
            ) from exc
        except ReqConnectionError as exc:
            raise HttpConnectionError(
                f"Upload connection error {filein.name} -> {url}: {exc}", url=url
            ) from exc
        except RequestException as exc:
            raise HttpClientError(
                f"Upload failed {filein.name} -> {url}: {exc}", url=url
            ) from exc
        return True

    def download_file(self, url: str, fileout: Path) -> bool:
        fileout.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.session.get(url, stream=True, timeout=self.upload_timeout) as rsp:
                rsp.raise_for_status()
                with fileout.open("wb") as fw:
                    for chunk in rsp.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            fw.write(chunk)
        except HTTPError as exc:
            r = exc.response
            raise HttpStatusError(
                f"Download failed {url} -> {fileout}: "
                f"{r.status_code if r is not None else '?'}",
                status=r.status_code if r is not None else None,
                url=url,
                response=r,
            ) from exc
        except ReqTimeout as exc:
            raise HttpTimeoutError(
                f"Download timed out {url} -> {fileout}: {exc}", url=url
            ) from exc
        except ReqConnectionError as exc:
            raise HttpConnectionError(
                f"Download connection error {url} -> {fileout}: {exc}", url=url
            ) from exc
        except RequestException as exc:
            raise HttpClientError(
                f"Download failed {url} -> {fileout}: {exc}", url=url
            ) from exc

        return True


def http_client[**P, R](
    func: Callable[Concatenate[HttpClient, P], R],
) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with HttpClient() as client:
            return func(client, *args, **kwargs)

    return wrapper


# ty не поддерживает higher-rank polymorphism для generic-функций,
# декорируемых через `Callable[Concatenate[..., P], R]`.
# Аннотация корректна, ограничение — в ty.
@http_client  # ty: ignore[invalid-argument-type]
def http_get[T](
    client: HttpClient, url: str, Model: type[T], data: dict | None = None
) -> T | list[T] | bytes | None:
    return client.get(url, Model, data)


# ty не поддерживает higher-rank polymorphism для generic-функций,
# декорируемых через `Callable[Concatenate[..., P], R]`.
# Аннотация корректна, ограничение — в ty.
@http_client  # ty: ignore[invalid-argument-type]
def http_post[T](
    client: HttpClient, url: str, Model: type[T], json: dict | None = None
) -> T | list[T] | bytes | None:
    return client.post(url, Model, json=json)
