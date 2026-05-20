.PHONY: up down build test seed migrate eval lint clean logs health

IMAGE_NAME ?= llm-observatory
TAG ?= local

up:
	docker compose up --build -d

down:
	docker compose down -v

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

test:
	pytest -q

seed:
	python demo/seed_data.py

migrate:
	alembic upgrade head

eval:
	@if [ -x .venv/bin/python ]; then .venv/bin/python evals/run_evals.py; else python3 evals/run_evals.py; fi

lint:
	ruff check . --ignore=F401 2>/dev/null || echo "Lint warnings noted"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete 2>/dev/null; \
	rm -f storage/ci_*.db storage/test_*.db storage/verify_*.db storage/hardening_*.db

logs:
	docker compose logs -f gateway

health:
	curl -s http://localhost:8001/health | python -m json.tool
