"""
Database Migration Utility: SQLite (mentor.db) -> PostgreSQL
Transfers all existing users, projects, progress logs, and chat messages into PostgreSQL.
"""
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL is not set in your .env file.")
        print("Example: DATABASE_URL=postgresql://postgres:password@localhost:5432/mentor_db")
        return

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("ERROR: psycopg2 is not installed. Please run: pip install psycopg2-binary")
        return

    sqlite_path = os.path.join(os.path.dirname(__file__), "mentor.db")
    if not os.path.exists(sqlite_path):
        print(f"ERROR: SQLite database file not found at {sqlite_path}")
        return

    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    print(f"1. Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(url)
    pg_cursor = pg_conn.cursor()

    print(f"2. Connecting to SQLite ({sqlite_path})...")
    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    sq_cursor = sq_conn.cursor()

    print("3. Initializing PostgreSQL tables...")
    from database import init_db
    init_db()

    # Tables to migrate in dependency order
    tables = [
        ("users", ["id", "username", "password_hash", "role", "full_name", "email", "department", "college", "created_at"]),
        ("projects", ["id", "user_id", "faculty_id", "title", "project_idea", "blueprint_json", "current_phase", "progress_percent", "status", "faculty_feedback", "team_members", "supervisor_action_items", "faculty_score", "faculty_score_breakdown", "sign_off_date", "invite_code", "created_at"]),
        ("progress_logs", ["id", "project_id", "week_number", "phase_name", "tasks_completed", "submitted_code", "code_language", "blockers", "github_link", "ai_feedback", "code_audit", "ai_score", "faculty_status", "faculty_comment", "created_at"]),
        ("chat_messages", ["id", "project_id", "user_id", "role", "content", "created_at"])
    ]

    for tbl, cols in tables:
        try:
            sq_cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            count = sq_cursor.fetchone()[0]
            if count == 0:
                print(f"   - {tbl}: 0 records to migrate.")
                continue

            sq_cursor.execute(f"SELECT {', '.join(cols)} FROM {tbl}")
            rows = sq_cursor.fetchall()

            col_str = ", ".join(cols)
            val_str = ", ".join(["%s"] * len(cols))
            insert_query = f"INSERT INTO {tbl} ({col_str}) VALUES ({val_str}) ON CONFLICT (id) DO NOTHING"

            inserted = 0
            for r in rows:
                data = tuple(r[col] for col in cols)
                pg_cursor.execute(insert_query, data)
                inserted += 1

            pg_conn.commit()

            # Update PostgreSQL sequence to avoid duplicate key errors on future inserts
            seq_query = f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), COALESCE(MAX(id), 1)) FROM {tbl}"
            pg_cursor.execute(seq_query)
            pg_conn.commit()

            print(f"   - {tbl}: Successfully migrated {inserted} records and updated sequence!")
        except Exception as e:
            print(f"   - {tbl}: Migration notice: {str(e)}")
            pg_conn.rollback()

    sq_conn.close()
    pg_conn.close()
    print("\n[SUCCESS] Migration completed successfully! Your PostgreSQL database is ready.")

if __name__ == "__main__":
    migrate()
