.PHONY: clean clean-build
SERVER_EXECUTABLE=grocery-scanner-server.pyz

clean: clean-build

clean-build:
	rm -rf build/

build: requirements.txt ## Install dependencies to build directory
	rm -f $(SERVER_EXECUTABLE)
	mkdir -p build/
	pip install -t build/ -r requirements.txt

$(SERVER_EXECUTABLE): build grocery_scanner/* ## Make the executable
	rm -r build/grocery_scanner
	cp -r grocery_scanner build/
	python3 -m zipapp --compress -p '/usr/bin/env python3' --output $(SERVER_EXECUTABLE) --main grocery_scanner.__main__:main build/

run: $(SERVER_EXECUTABLE) grocery-scanner.ini ## Run the server
	./grocery-scanner.ini

help: ## You are here
	    @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'
