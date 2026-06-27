import os
import sqlite3
import shutil
from pathlib import Path

def main():
    print("Running pre-start database check...")
    
    db_path = Path("/app/data/app.db")
    if not db_path.exists():
        db_path = Path("./data/app.db")
        
    if not db_path.exists():
        print("No database file found. Proceeding with fresh deployment.")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        has_alembic = "alembic_version" in tables
        has_users = "users" in tables or "documents" in tables
        
        if has_users and not has_alembic:
            print("WARNING: Legacy corrupted database detected (has tables but no alembic_version).")
            print("Resetting database to allow Alembic migrations to run clean...")
            if db_path.exists():
                os.remove(str(db_path))
                print(f"Successfully deleted corrupted database: {db_path}")
                
            chroma_dir = Path("/app/data/chroma")
            if not chroma_dir.exists():
                chroma_dir = Path("./data/chroma")
            if chroma_dir.exists():
                shutil.rmtree(str(chroma_dir))
                print("Successfully deleted outdated Chroma vector directory.")
        else:
            print("Database check passed. Database is clean or already managed by Alembic.")
            
    except Exception as e:
        print(f"Error during database pre-start check: {e}")

if __name__ == "__main__":
    main()
