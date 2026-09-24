.PHONY: clean clean-build clean-pyc test install debug
SERVER_EXECUTABLE=./grocery-scanner-server.pyz
VIRTUAL_ENV := ~/venvs/grocery_scanner

help: ## You are here
	@grep -E '^[^: 	]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

clean-build: ## Remove python build artifacts
	rm -rf build/
	rm -rf *.egg-info
	rm -rf $(SERVER_EXECUTABLE)

clean-pyc: ## Remove python bytecode artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.py[co]' -exec rm -f {} +

clean: clean-build clean-pyc ## Clean EVERYTHING

pip: ## Download a standalone zipapp of pip to avoid whatever shenanigans with system-wide pip
	curl 'https://bootstrap.pypa.io/pip/pip.pyz' -o pip

runtime_deps: pip pyproject.toml grocery_scanner/* ## Create runtime_deps directory
	python3 pip install --no-cache-dir --compile -U -t $@/ .

$(SERVER_EXECUTABLE): runtime_deps ## Make a single-file executable ready to run
	python3 -m zipapp --compress -p '/usr/bin/env -S python3 -OO' --output $(SERVER_EXECUTABLE) --main 'grocery_scanner.bottle_entrypoint:main' runtime_deps/

run: $(SERVER_EXECUTABLE) ## Make a single-file executable ready to run
	$(SERVER_EXECUTABLE) -c config.ini grocery_list.md

test: ## Run all tests. Might be broken up into unit, integration and end-to-end tests some day.
	python3 -m unittest discover tests

$(VIRTUAL_ENV):
	python3 -m venv $(VIRTUAL_ENV)

install: $(VIRTUAL_ENV) ## Install an editable version to .venv for quicker iteration.
	$(VIRTUAL_ENV)/bin/pip install -e .

debug: $(VIRTUAL_ENV)/bin/grocery-scanner-web ## Run the server with sample config settings
	@$(VIRTUAL_ENV)/bin/grocery-scanner-web -c config.ini grocery_list.md
