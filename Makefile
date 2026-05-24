.PHONY: dev backend frontend bootstrap install test test-cov lint setup backup hash

# First-time setup: install deps + bootstrap database + hash files
setup:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
	cd backend && python -m app.services.bootstrap
	$(MAKE) hash
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

# Backup database (snapshot to vault/backups/)
backup:
	@cd backend && python -c "\
	from app.services.backup import backup_database; \
	path = backup_database(); \
	print(f'Backup: {path}')"

# Hash all audio files for auto-heal
hash:
	@cd backend && python -c "\
	from app.database import SessionLocal; \
	from app.services.backup import hash_all_files; \
	db = SessionLocal(); \
	stats = hash_all_files(db); \
	print(f'Hashed: {stats[\"newly_hashed\"]} new, {stats[\"already_hashed\"]} cached, {stats[\"missing_files\"]} missing'); \
	db.close()"

# Run tests
test:
	cd backend && pytest tests/ -v

# Run tests with coverage (terminal + HTML report at backend/htmlcov/)
test-cov:
	cd backend && pytest tests -v --cov=app --cov-report=term --cov-report=html

# Lint backend (strict) + frontend typecheck (best-effort; pre-existing TS errors)
lint:
	cd backend && ruff check . && cd ../frontend && npx tsc --noEmit || true
