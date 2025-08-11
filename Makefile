.PHONY: clean clean-pyc
SERVER_EXECUTABLE=grocery-scanner-server.pyz

clean-pyc: ## Remove python file artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.py[co]' -exec rm -f {} +

clean: clean-pyc ## Clean build directory, python artifacts, EVERYTHING.

$(SERVER_EXECUTABLE): pyproject.toml grocery_scanner/* ## Make the executable
	mkdir -p build/
	pip install -U -t build/ .
	mv build/bin/cli build/__main__.py
	python3 -m zipapp --compress -p '/usr/bin/env python3' --output $(SERVER_EXECUTABLE) build/

run: $(SERVER_EXECUTABLE) grocery-scanner.ini ## Run the server
	./grocery-scanner.ini

test: ## Run all tests. Might be broken up into unit, integration and end-to-end tests some day.
	python3 -m unittest discover tests

help: ## You are here
	    @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'
