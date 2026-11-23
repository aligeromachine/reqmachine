# Changelog

All notable changes to **reqmachine** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- `http_get` передавал третий аргумент в `params` под именем `data` — параметр переименован в `params`
- `upload_file` молча терял `meta`, если не задан `key` — теперь `ValueError`
- Ошибки валидации бросаются как `HttpValidationError(HttpClientError)` вместо `TypeError`
- Скалярный JSON (строка/число) вместо объекта/массива — `HttpDecodeError`, аннотациям больше не противоречит
- `scripts/smoke_offline.py` обновлён под текущий API (ранее падал)

### Added
- `py.typed` (PEP 561) — пакет теперь реально типизирован для потребителей
- Валидаторы кэшируются по модели (`lru_cache`) — не пересобираются на каждый ответ
- `uv build` в CI; `ty` и `pytest-cov` в dev-группе (цели `just lint` / `just test-cov`)

## [0.1.6] - 2026-11

### Changed
- orjson → msgspec (парсинг JSON и `msgspec.convert` для валидации)
- Backend сборки — `uv_build`

### Added
- Типизированная валидация ответов: `client.get(url, Model)`, `DictValidator` / `ListValidator`
- `validate/` (`adapter.py`), `core/` (`config.py`, `types.py`), `errors/`

## [0.1.7] - 2026-11

### Added
- Публикация на PyPI через GitHub Release + Trusted Publishing
- Исключения вместо логирования: `HttpStatusError`, `HttpConnectionError`, `HttpTimeoutError`, `HttpDecodeError` (базовый `HttpClientError`)
- Django-сервис тестовых эндпоинтов в `service/`

### Added
- Start **reqmachine** project
