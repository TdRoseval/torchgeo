.PHONY: tests docs

tests:
	black --check .
	isort . --check --diff
	flake8 .
	pydocstyle .
	mypy .
	pytest --cov=. --cov-report=term-missing

docs:
	$(MAKE) -C docs html
