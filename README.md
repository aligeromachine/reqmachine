# Welcome to **`reqmachine`**

A small [requests](https://requests.readthedocs.io/)-based HTTP client with
retries, JSON parsing ([orjson](https://github.com/ijl/orjson)) and file
upload/download helpers.

Requires Python **3.14+**.

## Install

```bash
uv add reqmachine
# or
pip install reqmachine
```

## Usage

`@http_client` injects a fresh `HttpClient` as the first argument.
`get/post/put/patch/delete` accept a type and return parsed data
(`None` for an empty body), raising `HttpClientError` subclasses on
failure. `http_get` / `http_post` are one-shot helpers.

```python
from dataclasses import dataclass
from reqmachine import HttpClient, http_client


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
    fetch_posts()
```

## Tuning

```python
from reqmachine import HttpClient

client = HttpClient(
    verify=True,  # TLS verification (default: off)
    timeout=(3.0, 60.0),  # (connect, read)
    retries=3,  # urllib3 Retry total
    headers={"Authorization": "Bearer <token>"},
)
```
### Test service (Django)

`service/` contains a small Django app that implements every endpoint
scenario the client tests exercise — useful for running the client
against a real local server:

```bash
uv run python service/manage.py runserver 8000
```

| Endpoint | Scenario |
|---|---|
| `GET /api/json/` | 200 + JSON |
| `GET /api/empty/` | 204, empty body → client returns `None` |
| `GET /api/html/` | non-JSON body → `HttpDecodeError` |
| `GET /api/invalid-json/` | broken JSON → `HttpDecodeError` |
| `GET /api/error/` | 500 + JSON → `HttpStatusError` |
| `/api/echo/` | GET/POST/PUT/PATCH/DELETE echo (POST → 201) |
| `GET,HEAD /api/ping/` | availability probe (200) |
| `ANY /api/redirect/` | 302 → `/api/ping/` |
| `GET /api/head-only/` | 405 on HEAD, 200 on GET |
| `POST /api/upload/` | multipart: `file` + `JSONData` metadata |
| `GET /api/download/<name>/` | streaming download of an uploaded file |
| `GET /api/payload/` | fixed 1 KiB binary payload |

Example with the client:


## Files

```python
from pathlib import Path
from reqmachine import HttpClient

with HttpClient() as client:
    client.upload_file("https://example.com/upload", Path("data.bin"))
    client.download_file("https://example.com/file", Path("out/file.bin"))
```

`upload_file` sends the file as multipart with a JSON metadata field
(`JSONData` by default). Both return `True` on success.

## Errors

All exceptions derive from `HttpClientError`:

| Exception | When |
|---|---|
| `HttpStatusError` | Status is not 2xx/3xx (`.status`, `.response`) |
| `HttpConnectionError` | Connection could not be established |
| `HttpTimeoutError` | Connect/read timeout |
| `HttpDecodeError` | Body is not valid JSON |

`is_url_available()` never raises — returns `False` on any network error.

## Development

```bash
uv sync
uv run ruff check .
uv run pytest
```

Local Django test service (`service/`, serves every endpoint scenario):

```bash
uv run python service/manage.py runserver 8000
```

## License

MIT — see [LICENSE](LICENSE).
