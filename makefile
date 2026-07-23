.PHONY: server dev install lint clean

install:
	pip install -r requirements.txt

server:
	uvicorn src.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

lint:
	python -c "import src.main" && echo "OK"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
