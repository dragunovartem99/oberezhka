.DEFAULT_GOAL := check
.PHONY: check fmt fmt-check lint test run migrate
check: fmt-check lint test
fmt:
	uv run ruff format .
fmt-check:
	uv run ruff format --check .
lint:
	uv run ruff check .
test:
	DJANGO_DEBUG=1 uv run python manage.py test
run:
	DJANGO_DEBUG=1 uv run python manage.py runserver 127.0.0.1:8000
migrate:
	DJANGO_DEBUG=1 uv run python manage.py migrate
