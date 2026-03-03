"""One-time script to add missing columns to database tables."""
from app.core.config import get_settings
from sqlalchemy import create_engine, text

s = get_settings()
engine = create_engine(s.DATABASE_URL)

with engine.connect() as conn:
    # Check dataset_uploads columns
    cols = [row[0] for row in conn.execute(text("DESCRIBE dataset_uploads"))]
    print("dataset_uploads columns:", cols)

    if "status" not in cols:
        conn.execute(text("ALTER TABLE dataset_uploads ADD COLUMN status VARCHAR(50) DEFAULT 'completed'"))
        print("  Added: status")
    if "error_message" not in cols:
        conn.execute(text("ALTER TABLE dataset_uploads ADD COLUMN error_message TEXT NULL"))
        print("  Added: error_message")
    if "processed_date" not in cols:
        conn.execute(text("ALTER TABLE dataset_uploads ADD COLUMN processed_date DATETIME NULL"))
        print("  Added: processed_date")

    conn.commit()
    print("Done!")
