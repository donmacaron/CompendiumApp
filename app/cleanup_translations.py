"""One-time cleanup: removes duplicate/orphaned translation records.
Keeps only the most recent translation per page."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models.translation import PageTranslation
from sqlalchemy import func

db = SessionLocal()

# Find the max id (most recent) per page
subq = db.query(
    PageTranslation.page_id,
    func.max(PageTranslation.id).label('max_id')
).group_by(PageTranslation.page_id).subquery()

keep_ids = [row.max_id for row in db.query(subq.c.max_id).all()]

to_delete = db.query(PageTranslation).filter(
    PageTranslation.id.notin_(keep_ids)
).all()

print(f"Found {len(to_delete)} orphaned translation(s) to delete.")
for t in to_delete:
    print(f"  - Deleting: page_id={t.page_id} lang={t.language} id={t.id}")
    db.delete(t)

db.commit()
print("Done. Translations cleaned up.")
db.close()
