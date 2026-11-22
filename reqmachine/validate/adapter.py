from __future__ import annotations

from functools import partial
from typing import Any

import msgspec


class _ContainerValidator[T, I, O]:
    """Общая часть для валидаторов контейнеров.

    - T — модель элемента;
    - I — ожидаемый входной контейнер (dict / list / ...);
    - O — тип результата (T для dict, list[T] для list, ...).
    """

    __slots__ = ("_convert", "_model", "_strict")

    _expected_type: type  # переопределяется в наследниках

    def __init__(self, Model: type[T], *, strict: bool = False) -> None:
        self._model = Model
        self._convert = partial(msgspec.convert, type=self._resolve_target(Model))
        self._strict = strict

    @staticmethod
    def _resolve_target(Model: type[T]) -> Any:
        raise NotImplementedError

    def __call__(
        self,
        response: I | None,
    ) -> O | None:
        if response is None:
            return None

        if not isinstance(response, self._expected_type):
            raise TypeError(
                f"{type(self).__name__}: ожидался "
                f"{self._expected_type.__name__} для {self._model.__name__}, "
                f"получен {type(response).__name__}"
            )

        try:
            return self._convert(response, strict=self._strict)
        except msgspec.ValidationError as e:
            raise TypeError(
                f"Валидация {type(self).__name__}["
                f"{self._model.__name__}] не прошла: {e}"
            ) from e


class DictValidator[T](_ContainerValidator[T, dict, T]):
    """Валидатор dict → T.

    Аналог pydantic.TypeAdapter для msgspec.convert.
    """

    __slots__ = ()
    _expected_type = dict

    @staticmethod
    def _resolve_target(Model: type[T]) -> type[T]:
        return Model


class ListValidator[T](_ContainerValidator[T, list, list[T]]):
    """Валидатор list → list[T].

    Аналог pydantic.TypeAdapter(list[T]) для msgspec.convert.
    """

    __slots__ = ()
    _expected_type = list

    @staticmethod
    def _resolve_target(Model: type[T]) -> type[list[T]]:
        return list[Model]  # ty: ignore[invalid-type-form]
