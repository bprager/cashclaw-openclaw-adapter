PYTHON ?= python3

.PHONY: test lint lint-md typecheck check

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

lint-md:
	pymarkdown -d md012,md013,md022,md031,md032,md041 scan .

typecheck:
	$(PYTHON) -m mypy

check: lint lint-md typecheck test
