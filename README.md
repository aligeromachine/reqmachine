# Welcome to **`reqmachine`**

A small [requests](https://requests.readthedocs.io/)-based HTTP client with
retries, JSON parsing ([orjson](https://github.com/ijl/orjson)) and file
upload/download helpers.

Requires Python **3.14+**.

> [!CAUTION]
> `reqmachine` is a Work In Progress (WIP)

## Install

```bash
uv add reqmachine
# or
pip install reqmachine
```

## Usage

### Context manager

```python
from reqmachine import HttpClient

with HttpClient() as client:
    users = client.get("https://jsonplaceholder.typicode.com/users")
    posts = client.get("https://jsonplaceholder.typicode.com/posts")
```

`get/post/put/patch/delete` return parsed JSON (`None` for an empty
response body) and raise `HttpClientError` subclasses on failure.

### Decorators

```python
from reqmachine import HttpClient, http_client, http_get

@http_client
def fetch_users(client: HttpClient):
    return client.get("https://jsonplaceholder.typicode.com/users")
```

`@http_client` injects a fresh `HttpClient` as the first argument;
`http_get` / `http_post` are one-shot helpers that open a client per call.

### Tuning

```python
from reqmachine import HttpClient

client = HttpClient(
    verify=True,                       # TLS verification (default: off)
    timeout=(3.0, 60.0),               # (connect, read)
    retries=3,                         # urllib3 Retry total
    headers={"Authorization": "Bearer <token>"},
)
```

Retries apply to `HEAD/GET/PUT/DELETE/OPTIONS/TRACE` on statuses
`429, 500, 502, 503, 504` (see `Config`).

### Files

```python
from pathlib import Path
from reqmachine import HttpClient

with HttpClient() as client:
    client.upload_file("https://example.com/upload", Path("data.bin"), tags=["x"])
    client.download_file("https://example.com/file", Path("out/file.bin"))
```

`upload_file` sends the file as multipart with a JSON metadata field
(`JSONData` by default) and uses a longer timeout.

## Error types

Errors are raised, not swallowed — all of them derive from
`HttpClientError`:

| Exception | When |
|---|---|
| `HttpStatusError` | Response status is not 2xx/3xx (`.status`, `.response`) |
| `HttpConnectionError` | Could not establish a connection |
| `HttpTimeoutError` | Connect/read timeout |
| `HttpDecodeError` | Response body is not valid JSON |
| `HttpClientError` | Base class / any other requests error |

```python
from reqmachine import HttpClient, HttpTimeoutError, HttpStatusError

with HttpClient() as client:
    try:
        data = client.get("https://example.com/api")
    except HttpStatusError as e:
        print("server said", e.status)
    except HttpTimeoutError:
        print("too slow")
```

`upload_file` / `download_file` raise the same exceptions and return
`True` on success. `is_url_available()` never raises — it returns
`False` on any network error.

## Development

```bash
uv sync
uv run ruff check .
uv run pytest
```

Быстрая проверка проброса ошибок без pytest/responses/сети:

```bash
python3 scripts/smoke_offline.py
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

```python
from reqmachine import HttpClient

with HttpClient(verify=False) as client:
    print(client.get("http://127.0.0.1:8000/api/json/"))
    client.upload_file("http://127.0.0.1:8000/api/upload/", path, tags=["demo"])
    client.download_file("http://127.0.0.1:8000/api/payload/", out)
```

Service tests: `uv run python service/manage.py test api`

## License

MIT — see [LICENSE](LICENSE).

