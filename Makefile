.PHONY: clean clean-pyc
SERVER_EXECUTABLE=grocery-scanner-server.pyz

help: ## You are here
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

clean-pyc: ## Remove python file artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.py[co]' -exec rm -f {} +

clean-pyz:
	rm -r pyz_build
	rm $(SERVER_EXECUTABLE)

clean: clean-pyc clean-pyz ## Clean build directory, python artifacts, EVERYTHING.

pip: ## Download a standalone zipapp of pip to avoid whatever shenanigans with system-wide pip
	curl 'https://bootstrap.pypa.io/pip/pip.pyz' -o pip

$(SERVER_EXECUTABLE): pip pyproject.toml grocery_scanner/* ## Make the executable
	python3 pip install -t pyz_build/ .
	mv pyz_build/bin/grocery-scanner-web pyz_build/__main__.py
	python3 -m zipapp --compress -p '/usr/bin/env python3' --output $(SERVER_EXECUTABLE) pyz_build/

run: $(SERVER_EXECUTABLE) grocery-scanner.ini ## Run the server
	./grocery-scanner.ini

test: ## Run all tests. Might be broken up into unit, integration and end-to-end tests some day.
	python3 -m unittest discover tests
