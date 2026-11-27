# Changelog

All notable changes to **reqmachine** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.9]

### Changed
- `Model=None` возвращает сырые байты тела — так же, как голые контейнеры; `requests.Response` больше не входит в типы возврата `HttpClient` (объект ответа при необходимости доступен через `client.session`)
- Нетипизированная `Model` — голый контейнер (`dict`, `list`, `tuple`, `set`, `frozenset`) — означает «без разбора»: тело ответа возвращается как есть (`bytes`), без декодирования и валидации; не-JSON ответ тоже не даёт ошибки. Типизированные формы работают как прежде: `list[dict]`, `list[MyModel]`, `dict[str, Any]`, `set[int]`; `typing.Any` декодирует любой JSON без валидации

### Fixed
- Array-like модели (`list[...]`, `tuple[...]`, `set[...]`) больше не собирают union `Model | list[Model]` с двумя array-like, который msgspec отвергает `TypeError`, — целью конвертации служит сама `Model`

## [0.1.8]

### Changed
- `DictValidator` / `ListValidator` заменены единым `JsonValidator`: универсальный валидатор JSON — на входе только bytes / str (декодирует сам и валидирует `Model | list[Model]`: dict -> `Model`, list -> `list[Model]`); про HTTP класс не знает
- `HttpClient` сам решает по Content-Type / первому байту, JSON ли тело: не-JSON отдаёт как `bytes`, JSON передаёт валидатору байтами и обогащает `HttpDecodeError` url/response

### Fixed
- Пустой JSON-контейнер (`{}` / `[]`) в ответе больше не превращается в `None`: falsy-проверка молча пропускала валидацию — теперь пустой объект/массив валидируется по модели как обычно
- `http_get` передавал третий аргумент в `params` под именем `data` — параметр переименован в `params`
- `upload_file` молча терял `meta`, если не задан `key` — теперь `ValueError`
- Ошибки валидации бросаются как `HttpValidationError(HttpClientError)` вместо `TypeError`
- Скалярный JSON (строка/число) вместо объекта/массива — `HttpDecodeError`, аннотациям больше не противоречит

### Added
- `Model=None` (теперь значение по умолчанию): тело ответа не парсится и не валидируется — методы возвращают сырой `requests.Response`
- `py.typed` (PEP 561) — пакет теперь реально типизирован для потребителей
- Валидаторы кэшируются по модели (`lru_cache`) — не пересобираются на каждый ответ
- `uv build` в CI; `ty` и `pytest-cov` в dev-группе (цели `just lint` / `just test-cov`)

## [0.1.7] - 2026-11

### Added
- Публикация на PyPI через GitHub Release + Trusted Publishing
- Исключения вместо логирования: `HttpStatusError`, `HttpConnectionError`, `HttpTimeoutError`, `HttpDecodeError` (базовый `HttpClientError`)
- Django-сервис тестовых эндпоинтов в `service/`

## [0.1.6] - 2026-11

### Changed
- orjson → msgspec (парсинг JSON и `msgspec.convert` для валидации)
- Backend сборки — `uv_build`

### Added
- Типизированная валидация ответов: `client.get(url, Model)`, `DictValidator` / `ListValidator`
- `validate/` (`adapter.py`), `core/` (`config.py`, `types.py`), `errors/`

### Added
- Start **reqmachine** project
