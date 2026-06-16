COMPOSE = docker compose -f docker/docker-compose.yml

dev-up:
	$(COMPOSE) up --build -d

dev-down:
	$(COMPOSE) down

dev-logs:
	$(COMPOSE) logs -f

dev-shell:
	$(COMPOSE) exec web /bin/bash

test:
	poetry run pytest -vv --maxfail=1

lint:
	poetry run ruff check src/

lint-fix:
	poetry run ruff check src/ --fix

format:
	poetry run ruff format src/

typecheck:
	poetry run mypy src/

ci: lint typecheck test
