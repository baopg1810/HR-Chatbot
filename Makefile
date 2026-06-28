.PHONY: run test lint format typecheck check clean

run:
	PYTHONPATH=backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	PYTHONPATH=backend pytest tests/ -v

lint:
	ruff check backend/app/ tests/

format:
	ruff format backend/app/ tests/

typecheck:
	PYTHONPATH=backend mypy backend/app/


check: lint format test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
