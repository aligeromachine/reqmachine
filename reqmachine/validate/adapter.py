from __future__ import annotations

from functools import partial

import msgspec

from ..errors.errors import HttpDecodeError, HttpValidationError


class JsonValidator[T]:
    """Декодирование и валидация JSON-документа по модели.

    Универсальный вход: bytes или str с текстом JSON (None — пустое
    тело). Про HTTP класс не знает: решение «JSON это или нет»
    принимает вызывающая сторона (HttpClient — по Content-Type и
    первому байту тела).

    Декодированный dict валидируется как T, list — как list[T]
    (union `Model | list[Model]` в msgspec.convert).
    """

    __slots__ = ("_convert", "_decode", "_model", "_strict")

    def __init__(self, Model: type[T], *, strict: bool = False) -> None:
        self._model = Model
        # type=dict | list: скалярный JSON ("ok", 123) отсекается самой
        # декодирующей стороной, ручная проверка не нужна
        self._decode = partial(msgspec.json.decode, type=dict | list)
        self._convert = partial(
            msgspec.convert,
            type=Model | list[Model],  # ty: ignore[invalid-type-form]
        )
        self._strict = strict

    def __call__(self, body: bytes | str | None) -> T | list[T] | None:
        if not body:
            return None

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
