#!/bin/bash
# Weekly maintenance check
# Usage: make weekly
#   or:  bash scripts/weekly-check.sh

set -e
cd "$(dirname "$0")/.."

echo "📋 Greenroom: Weekly Health Check"
echo "===================================="
echo ""

# 1. Rescan for any new files
echo "1. Scanning filesystem..."
cd backend && python -c "
from app.services.bootstrap import run_bootstrap
run_bootstrap()
" 2>&1 | tail -5
echo ""

# 2. Check file health
echo "2. Checking file health..."
python -c "
from app.database import SessionLocal
from app.services.file_manager import health_check
db = SessionLocal()
broken = health_check(db)
if broken:
    print(f'   ⚠️  {len(broken)} broken file links found!')
    for b in broken[:5]:
        print(f'      {b.song_title or \"Unknown\"}: {b.path.split(\"/\")[-1]}')
    if len(broken) > 5:
        print(f'      ...and {len(broken)-5} more')
    print('   Run auto-heal from the Dashboard to fix.')
else:
    print('   ✓ All file links healthy')
db.close()
"
echo ""

# 3. Hash any unhashed files
echo "3. Checking content hashes..."
python -c "
from app.database import SessionLocal
from app.services.backup import hash_all_files
db = SessionLocal()
stats = hash_all_files(db)
if stats['newly_hashed'] > 0:
    print(f'   Hashed {stats[\"newly_hashed\"]} new files')
else:
    print(f'   ✓ All {stats[\"already_hashed\"]} files hashed')
if stats['missing_files'] > 0:
    print(f'   ⚠️  {stats[\"missing_files\"]} files missing from disk')
db.close()
"
echo ""

# 4. Export annotations
echo "4. Exporting annotations..."
python -c "
from app.database import SessionLocal
from app.services.backup import export_annotations
import json
from pathlib import Path
db = SessionLocal()
result = export_annotations(db)
Path('../exports/annotations_latest.json').write_text(json.dumps(result['data'], indent=2))
print(f'   {len(result[\"data\"][\"songs\"])} songs, {len(result[\"data\"][\"takes\"])} takes')
db.close()
"
echo ""

# 5. Backup database
echo "5. Backing up database..."
python -c "
from app.services.backup import backup_database, list_backups
path = backup_database()
backups = list_backups()
print(f'   Saved ({len(backups)} backups total)')
"
echo ""

# 6. Summary stats
echo "6. Portfolio summary..."
python -c "
from app.database import SessionLocal
from sqlalchemy import func
from app.models import Song, Take, PracticeSession, AudioFile, TriageItem
db = SessionLocal()
print(f'   Songs:     {db.query(func.count(Song.id)).scalar()}')
print(f'   Sessions:  {db.query(func.count(PracticeSession.id)).scalar()}')
print(f'   Takes:     {db.query(func.count(Take.id)).scalar()}')
print(f'   Audio:     {db.query(func.count(AudioFile.id)).scalar()}')
rated = db.query(func.count(Take.id)).filter(Take.rating_overall.isnot(None)).scalar()
total = db.query(func.count(Take.id)).scalar()
print(f'   Rated:     {rated}/{total} takes ({round(rated/max(total,1)*100)}%)')
triage = db.query(func.count(TriageItem.id)).filter(TriageItem.status=='pending').scalar()
if triage > 0:
    print(f'   Triage:    {triage} files need classification')
db.close()
"
echo ""

# 7. Git status
echo "7. Git status..."
cd ..
git add exports/annotations_latest.json
if git diff --cached --quiet; then
    echo "   No changes since last commit"
else
    git commit -m "weekly: update annotations $(date +%Y-%m-%d)"
    echo "   Committed annotation updates"
fi

UNPUSHED=$(git log origin/main..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')
if [ "$UNPUSHED" -gt 0 ]; then
    echo "   ⚠️  $UNPUSHED unpushed commits — run 'git push'"
else
    echo "   ✓ Up to date with remote"
fi
echo ""

echo "===================================="
echo "✓ Weekly check complete!"
