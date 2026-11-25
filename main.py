from __future__ import annotations

import time
from dataclasses import dataclass

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
    """
    validator = JsonValidator(Todo)

    # bytes — например, содержимое файла: Path("todo.json").read_bytes()
    one = validator(b'{"id": 1, "title": "delectus", "completed": false}')
    print("bytes:", one)

    # str — например, JSON из конфига
    raw = '{"id": 2, "title": "quis ut nam", "completed": true}'
    print("str:  ", validator(raw))

    # массив объектов -> list[Todo]
    print("list: ", validator('[{"id": 3, "title": "third", "completed": false}]'))

    # несоответствие модели -> HttpValidationError
    try:
        validator(b'{"id": "not an int", "title": "x", "completed": true}')
    except HttpValidationError as exc:
        print("error:", exc)


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

    with Timer("fetch_posts") as _:
        fetch_posts()
