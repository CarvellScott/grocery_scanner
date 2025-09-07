.PHONY: clean clean-build clean-pyc executable
SERVER_EXECUTABLE=grocery-scanner-server

help: ## You are here
	@grep -E '^[^: 	]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

clean-build: ## Remove python build artifacts
	rm -rf build/
	rm -rf *.egg-info
	rm -rf $(SERVER_EXECUTABLE) $(SERVER_EXECUTABLE).pyz

clean-pyc: ## Remove python bytecode artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.py[co]' -exec rm -f {} +

clean: clean-build clean-pyc ## Clean EVERYTHING

pip: ## Download a standalone zipapp of pip to avoid whatever shenanigans with system-wide pip
	curl 'https://bootstrap.pypa.io/pip/pip.pyz' -o pip

$(SERVER_EXECUTABLE).pyz: pip pyproject.toml grocery_scanner/* 
	python3 pip install --no-cache-dir --compile -U -t $(SERVER_EXECUTABLE)/ .
	python3 -m zipapp --compress -p '/usr/bin/env -S python3 -OO' --output $(SERVER_EXECUTABLE).pyz --main 'grocery_scanner.bottle_entrypoint:main' $(SERVER_EXECUTABLE)/

executable: $(SERVER_EXECUTABLE).pyz ## Make a single-file executable ready to run

test: ## Run all tests. Might be broken up into unit, integration and end-to-end tests some day.
	python3 -m unittest discover tests

.venv:
	python3 -m venv .venv

install: .venv ## Install an editable version to .venv for quicker iteration.
	.venv/bin/pip install -e .

config.ini: .venv ## Create a sample config from scratch
	echo "#!/usr/bin/env -S .venv/bin/grocery-scanner-web -p 8080" > config.ini
	chmod +x config.ini

run: config.ini ## Run the server with sample config settings
	./config.ini
