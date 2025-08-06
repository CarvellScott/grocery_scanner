.PHONY: clean clean-build clean-pyc
SERVER_EXECUTABLE=grocery-scanner-server.pyz

clean-build: # Clean directory used to build the executable.
	rm -rf build/

clean-pyc: # Remove python file artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.py[co]' -exec rm -f {} +

clean: clean-build clean-pyc # Clean build directory, python artifacts, EVERYTHING.

build: requirements.txt ## Install dependencies to build directory
	rm -f $(SERVER_EXECUTABLE)
	mkdir -p build/
	pip install -t build/ -r requirements.txt

$(SERVER_EXECUTABLE): build grocery_scanner/* ## Make the executable
	rm -rf build/grocery_scanner
	cp -r grocery_scanner build/
	python3 -m zipapp --compress -p '/usr/bin/env python3' --output $(SERVER_EXECUTABLE) --main grocery_scanner.__main__:main build/

run: $(SERVER_EXECUTABLE) grocery-scanner.ini ## Run the server
	./grocery-scanner.ini

test: # Run all tests. Might be broken up into unit, integration and end-to-end tests some day.
	python3 -m unittest discover tests

help: ## You are here
	    @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'
