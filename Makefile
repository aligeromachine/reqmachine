.DEFAULT_GOAL := help
.PHONY: help sync lint smoke test test-service check serve build release

help: ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

sync: ## Установить зависимости (uv sync)
	uv sync

lint: ## Линтер ruff
	uv run ruff check .

test: ## Тесты клиента (pytest)
	uv run pytest

test-service: ## Тесты Django-сервиса
	uv run python service/manage.py test api

check: lint smoke test test-service ## Вся проверка: lint + smoke + pytest + Django
	uv run --no-project --with dist/reqmachine-0.1.5-py3-none-any.whl python -c "from reqmachine import HttpClient; print('OK')"

serve: ## Запустить Django-сервис на 127.0.0.1:8000
	uv run python service/manage.py runserver 8000

build: ## Собрать sdist и wheel в dist/
	uv build

release: ## Публикация релиза: make release TAG=v0.1.0 (тег -> publish.yml -> PyPI)
	git tag $(TAG)
	git push origin $(TAG)
