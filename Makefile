MAP ?= maps/easy/01_linear_path.txt

.PHONY: install run gui debug clean lint lint-strict test

install:
	uv sync

run:
	uv run fly-in "$(MAP)"

gui:
	uv run fly-in "$(MAP)" --gui

debug:
	uv run python -m pdb -m fly_in.main "$(MAP)"

clean:
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

test:
	uv run pytest
