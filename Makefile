.PHONY: test lint format mypy migrate run docker-build docker-up

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

mypy:
	mypy app tests

migrate:
	alembic upgrade head

run:
	python -m app.main

docker-build:
	docker compose build

docker-up:
	docker compose up --build

