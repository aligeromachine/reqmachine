from __future__ import annotations
from dataclasses import dataclass

import time
from reqmachine import HttpClient, http_client

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
    catchPhrase: str   # имя как в JSON (camelCase — валидный идентификатор Python)
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
    with Timer('fetch_posts') as _:
        fetch_posts()
