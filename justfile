# justfile

# Показать список всех команд
default:
    @just --list

# Синхронизировать зависимости (создать .venv и установить всё)
sync:
    uv sync --all-groups

# Добавить пакет в зависимости (пример: just add requests)
add package:
    uv add {{package}}

run:
    uv run main.py

lint *args:
    uv run ruff check {{args}} .
    uv run ruff format --check .
    uv run ty check

# Отформатировать код и применить автоисправления
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# Запустить тесты
test *args:
    uv run pytest tests/ {{args}} -v

# Запустить тесты с покрытием
test-cov:
    uv run pytest tests/ --cov

test-srv: ## Тесты Django-сервиса
	uv run python service/manage.py test api

test-all: test test-srv

serve:
	uv run python service/manage.py runserver 8000

build:
	uv build

check *args: 
    uv run --no-project --with dist/reqmachine-{{args}}-py3-none-any.whl python -c "from reqmachine import HttpClient; print('OK')"

# Мягкая очистка: окружение и артефакты, лок-файл и кеш uv сохраняются
clean:
    rm -rf .venv .pytest_cache .ruff_cache
    find . -type d -name __pycache__ -prune -exec rm -rf {} +

# Жёсткий сброс: ещё и лок-файл, и глобальный кеш uv
nuke: clean
    rm -f uv.lock
    uv cache clean

release *args:
	git tag {{args}}
	git push origin {{args}}
