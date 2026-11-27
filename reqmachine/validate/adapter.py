from __future__ import annotations

from functools import partial
from typing import Any, get_origin, overload

import msgspec

from ..errors.errors import HttpDecodeError, HttpValidationError

# Голые контейнеры не несут информации о типе: Model без типа
# означает «без разбора» — тело возвращается как есть
_BARE_CONTAINERS = (dict, list, tuple, set, frozenset)

# Array-like origins: для них union `Model | list[Model]` собрать
# нельзя — msgspec отвергает два array-like в одном union
_ARRAY_LIKE = (list, tuple, set, frozenset)


class JsonValidator[T]:
    """Декодирование и валидация JSON-документа по модели.

    Универсальный вход: bytes или str с текстом JSON (None — пустое
    тело). Про HTTP класс не знает: решение «JSON это или нет»
    принимает вызывающая сторона (HttpClient — по Content-Type и
    первому байту тела).

    Типизированная модель (dataclass, msgspec.Struct, int,
    dict[str, Any], list[dict], set[int], ...): декодированный dict
    валидируется как T, list — как list[T] (union `Model |
    list[Model]` в msgspec.convert). Для array-like алиасов union
    невозможен — msgspec отвергает два array-like, поэтому целью
    служит сама Model: массив -> list[dict] / set[int] / ...,
    объект -> HttpValidationError.

    Нетипизированная Model — голый контейнер (dict, list, tuple,
    set, frozenset): парсить нечего, тело возвращается как есть
    (bytes -> bytes, str -> str). Разбирает ли сервер JSON — роли
    не играет: сырой ответ в байтах годится для любой формы.

    Любая форма JSON без валидации элементов — `typing.Any`:
    декодирует, но не проверяет.
    """

    __slots__ = ("_convert", "_decode", "_model", "_raw", "_strict")

    def __init__(self, Model: type[T], *, strict: bool = False) -> None:
        self._model = Model
        self._raw = Model in _BARE_CONTAINERS
        self._strict = strict
        if self._raw:
            # Нетипизированная Model: парсить нечего —
            # декодер и конвертер не строятся вовсе
            return
        # type=dict | list: скалярный JSON ("ok", 123) отсекается самой
        # декодирующей стороной, ручная проверка не нужна
        self._decode = partial(msgspec.json.decode, type=dict | list)
        self._convert = partial(
            msgspec.convert,
            type=self._resolve_target(Model),
        )

    @staticmethod
    def _resolve_target(Model: type[T]) -> Any:
        # Для array-like алиасов (list[...], tuple[...], set[...]) union
        # `Model | list[Model]` содержит два array-like и отвергается
        # msgspec (TypeError) — целью служит сама Model:
        # массив -> Model, объект -> HttpValidationError.
        if get_origin(Model) in _ARRAY_LIKE:
            return Model
        return Model | list[Model]  # ty: ignore[invalid-type-form]

    @overload
    def __call__(self, body: bytes | None) -> T | list[T] | bytes | None: ...

    @overload
    def __call__(self, body: str) -> T | list[T] | str: ...

    def __call__(self, body: bytes | str | None) -> T | list[T] | bytes | str | None:
        if not body:
            return None

        # Нетипизированная Model: парсить не нужно — тело как есть
        if self._raw:
            return body

        # ValidationError — подкласс DecodeError, поэтому ловим его первым
        try:
            decoded = self._decode(body)
        except msgspec.ValidationError as exc:
            raise HttpDecodeError(f"Expected JSON object or array: {exc}") from exc
        except msgspec.DecodeError as exc:
            raise HttpDecodeError(f"Invalid JSON: {exc}") from exc

        try:
            return self._convert(decoded, strict=self._strict)
        except msgspec.ValidationError as e:
            raise HttpValidationError(
                f"Валидация JsonValidator[{self._model.__name__}] не прошла: {e}"
            ) from e
