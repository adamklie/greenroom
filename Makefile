.PHONY: dev backend frontend bootstrap install test setup export backup after-practice weekly

# First-time setup: install deps + bootstrap database + hash files
setup:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
	cd backend && python -m app.services.bootstrap
	$(MAKE) hash
	$(MAKE) export
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

# Export annotations to git-tracked JSON
export:
	@cd backend && python -c "\
	from app.database import SessionLocal; \
	from app.services.backup import export_annotations; \
	import json; \
	from pathlib import Path; \
	db = SessionLocal(); \
	result = export_annotations(db); \
	Path('../exports/annotations_latest.json').write_text(json.dumps(result['data'], indent=2)); \
	print(f'Exported {len(result[\"data\"][\"songs\"])} songs, {len(result[\"data\"][\"takes\"])} takes to exports/annotations_latest.json'); \
	db.close()"

# Backup database
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

# Post-practice routine: rescan, hash, export, backup, commit
after-practice:
	bash scripts/after-practice.sh

# Weekly health check: scan, check links, hash, export, summary
weekly:
	bash scripts/weekly-check.sh

# Run tests
test:
	cd backend && pytest tests/ -v
