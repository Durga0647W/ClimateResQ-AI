"""Generate the 250-row dataset and seed a fast demo subset into SQLite."""
import csv, sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from database.database import init_db, get_db
from database.models import Incident
from utils.pipeline import run_pipeline

def seed(limit=250):
    from data.generate_demo_data import out as csv_path
    if not csv_path.exists():
        import subprocess
        subprocess.run([sys.executable,"data/generate_demo_data.py"],check=True)
    init_db()
    db=get_db()
    from database.models import Report
    if db.query(Report).count() >= limit:
        db.close(); return
    with csv_path.open(encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    for i, row in enumerate(rows[:limit]):
        try: ts=datetime.fromisoformat(row["timestamp"])
        except Exception: ts=datetime.utcnow()
        try: ppl=int(row.get("people_affected") or 0)
        except Exception: ppl=0
        desc=row["description"]; loc=row["location"]; src=row["source_type"]
        if not desc or len(desc)<5: continue
        reporter_id = f"citizen_demo_{i+1:03d}"
        try: run_pipeline(desc,loc,ts,src,ppl,db, reporter_id=reporter_id)
        except Exception as exc: print("Seed warning:",exc)
    db.close()

if __name__=="__main__":
    seed()
    print("Demo database ready.")
