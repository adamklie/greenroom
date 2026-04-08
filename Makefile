.PHONY: dev backend frontend bootstrap install test setup

# First-time setup: install deps + bootstrap database
setup:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
	cd backend && python -m app.services.bootstrap
	@echo ""
	@echo "✓ Setup complete! Run 'make dev' to start Greenroom."

# Install dependencies only
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# Run both servers in parallel (Ctrl+C stops both)
dev:
	@echo "Starting Greenroom..."
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo ""
	@(cd backend && uvicorn app.main:app --reload --port 8000 &) && \
	 (cd frontend && npx vite --port 5173)

# Run backend only
backend:
	cd backend && uvicorn app.main:app --reload --port 8000

# Run frontend only
frontend:
	cd frontend && npx vite --port 5173

# Bootstrap database from filesystem
bootstrap:
	cd backend && python -m app.services.bootstrap

# Run tests
test:
	cd backend && pytest tests/ -v
