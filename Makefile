.PHONY: dev backend frontend bootstrap install test

# Install all dependencies
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# Run backend dev server
backend:
	cd backend && uvicorn app.main:app --reload --port 8000

# Run frontend dev server
frontend:
	cd frontend && npm run dev

# Run both servers (requires two terminals, or use this with &)
dev:
	@echo "Run 'make backend' and 'make frontend' in separate terminals"

# Bootstrap database from filesystem
bootstrap:
	cd backend && python -m app.services.bootstrap

# Run tests
test:
	cd backend && pytest tests/ -v
