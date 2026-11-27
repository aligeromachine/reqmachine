from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from reqmachine import HttpClient, HttpValidationError, JsonValidator, http_client


class Timer:
    def __init__(self, name=""):
        self.name = name

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        print(f"{self.name}: {time.perf_counter() - self.start:.4f} c")


@dataclass
class Geo:
    lat: str
    lng: str


@dataclass
class Address:
    street: str
    suite: str
    city: str
    zipcode: str
    geo: Geo


@dataclass
class Company:
    name: str
    catchPhrase: str  # имя как в JSON (camelCase — валидный идентификатор Python)
    bs: str


@dataclass
class User:
    id: int
    name: str
    username: str
    email: str
    address: Address
    phone: str
    website: str
    company: Company


@dataclass
class Post:
    id: int
    userId: int
    title: str
    body: str


@dataclass
class Todo:
    id: int
    title: str
    completed: bool


def validate_offline() -> None:
    """JsonValidator отдельно от клиента: bytes / str -> модель.

    Про HTTP класс не знает — годится для любых задач, где на руках
    JSON: файлы, конфиги, ответы сторонних клиентов.

    Демонстрация всех режимов Model.
    """
    todo_json = b'{"id": 1, "title": "delectus", "completed": false}'
    todos_json = '[{"id": 2, "title": "quis ut nam", "completed": true}]'

    # ── типизированная Model: декодирование + валидация ──
    print("dataclass:      ", JsonValidator(Todo)(todo_json))
    print("list[Todo]:     ", JsonValidator(list[Todo])(todos_json))
    print("dict[str, Any]: ", JsonValidator(dict[str, Any])(todo_json))
    print("set[int]:       ", JsonValidator(set[int])(b"[3, 1, 3, 2]"))

    # ── typing.Any: декодирует любой JSON, ничего не проверяет ──
    print("Any:            ", JsonValidator(Any)('{"mixed": [1, "x", null]}'))

    # ── голый контейнер (нетипизированная Model): без разбора ──
    print("голый dict:     ", JsonValidator(dict)(todo_json))
    print("голый list:     ", JsonValidator(list)(todos_json))

    # ── несоответствие модели -> HttpValidationError ──
    try:
        JsonValidator(Todo)(b'{"id": "not an int", "title": "x", "completed": true}')
    except HttpValidationError as exc:
        print("ошибка валидации:", exc)


@http_client
def fetch_modes(client: HttpClient):
    """Режимы Model на живом запросе (нужна сеть).

    Возврат клиента — `T | list[T] | bytes | None`: нетипизированная
    Model даёт сырые байты, типизированная — разобранные данные.
    Перед использованием результат сужают через isinstance.
    """
    url = "https://jsonplaceholder.typicode.com/users"

    # Model=None (по умолчанию): без разбора — сырые байты тела
    body = client.get(url)
    assert isinstance(body, bytes)
    print("bytes:      ", body[:48], b"...")

    # голый dict — то же самое: без разбора
    raw = client.get(url, dict)
    assert isinstance(raw, bytes)
    print("голый dict: ", raw[:48], b"...")

    # list[dict]: разобранный список словарей, поля не проверяются
    users = client.get(url, list[dict])
    assert isinstance(users, list)
    first = users[0]
    assert isinstance(first, dict)
    print("list[dict]: ", len(users), "users, first:", first["name"])


@http_client
def fetch_posts(client: HttpClient):
    users = client.get("https://jsonplaceholder.typicode.com/users", User)
    if isinstance(users, list):
        for it in users:
            print(it.company)

    posts = client.get("https://jsonplaceholder.typicode.com/posts", Post)
    if isinstance(posts, list):
        for it in posts:
            print(it.title)


if __name__ == "__main__":
    # локальная часть — работает без сети
    with Timer("validate_offline") as _:
        validate_offline()

    # сетевые демо
    with Timer("fetch_modes") as _:
        fetch_modes()

    with Timer("fetch_posts") as _:
        fetch_posts()
