.PHONY: clean clean-build
SERVER_EXECUTABLE=grocery-scanner-server.pyz

clean: clean-build

clean-build:
	rm -rf build/
	rm -rf dist/

build-intensifies:
	python3 setup.py sdist
	tar tzf dist/python_intensifies*
	twine check dist/*

deploy-intensifies:
	# twine upload dist/*

build: requirements.txt
	rm -f $(SERVER_EXECUTABLE)
	mkdir -p build/
	pip install -t build/ -r requirements.txt

## Make the executable
$(SERVER_EXECUTABLE): build grocery_scanner/__main__.py
	cp -r grocery_scanner build/
	python3 -m zipapp --compress -p '/usr/bin/env python3' --output $(SERVER_EXECUTABLE) --main grocery_scanner.__main__:main build/


deploy-grocery-scanner: $(SERVER_EXECUTABLE)
	scp -P 8022 grocery-scanner.ini $(SERVER_EXECUTABLE) 192.168.1.6:

run: $(SERVER_EXECUTABLE) grocery-scanner.ini
	./grocery-scanner.ini

test:
	./rpgp_tests.py

help: ## You are here
	    @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'
