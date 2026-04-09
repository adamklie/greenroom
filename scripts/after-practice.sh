#!/bin/bash
# Run after every practice session
# Usage: make after-practice
#   or:  bash scripts/after-practice.sh

set -e
cd "$(dirname "$0")/.."

echo "🎸 Greenroom: Post-Practice Routine"
echo "===================================="
echo ""

# 1. Rescan filesystem for new files
echo "1. Scanning for new files..."
cd backend && python -c "
from app.services.bootstrap import run_bootstrap
run_bootstrap()
" 2>&1 | tail -5
echo ""

# 2. Hash any new files
echo "2. Hashing new files..."
python -c "
from app.database import SessionLocal
from app.services.backup import hash_all_files
db = SessionLocal()
stats = hash_all_files(db)
print(f'   {stats[\"newly_hashed\"]} new files hashed, {stats[\"already_hashed\"]} already cached')
db.close()
"
echo ""

# 3. Export annotations
echo "3. Exporting annotations..."
python -c "
from app.database import SessionLocal
from app.services.backup import export_annotations
import json
from pathlib import Path
db = SessionLocal()
result = export_annotations(db)
Path('../exports/annotations_latest.json').write_text(json.dumps(result['data'], indent=2))
print(f'   {len(result[\"data\"][\"songs\"])} songs, {len(result[\"data\"][\"takes\"])} takes exported')
db.close()
"
echo ""

# 4. Backup database
echo "4. Backing up database..."
python -c "
from app.services.backup import backup_database
path = backup_database()
print(f'   Saved to {path}')
"
echo ""

# 5. Git commit
echo "5. Committing to git..."
cd ..
git add exports/annotations_latest.json
if git diff --cached --quiet; then
    echo "   No annotation changes to commit"
else
    git commit -m "post-practice: update annotations $(date +%Y-%m-%d)"
    echo "   Committed!"
fi
echo ""

echo "===================================="
echo "✓ Post-practice routine complete!"
echo ""
echo "Next steps:"
echo "  - Open http://localhost:5173 to rate your takes"
echo "  - Use the Process page if you have new GoPro videos"
echo "  - git push when ready"
