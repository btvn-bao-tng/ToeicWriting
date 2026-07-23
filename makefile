.PHONY: server dev install build lint clean

install:
	pip install -r requirements.txt
	npm install

build:
	npm run build

server: build
	uvicorn src.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

clean:
	rm -rf node_modules src/static/dist __pycache__ src/**/__pycache__
