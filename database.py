import sqlite3
import hashlib
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

DB_PATH = os.path.join(os.path.dirname(__file__), "mentor.db")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

def is_postgres() -> bool:
    return bool(DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")))

class PgRow(dict):
    def __init__(self, d):
        super().__init__(d)
        self._values = list(d.values())

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._values[item]
        return super().__getitem__(item)

class PgCursorWrapper:
    def __init__(self, real_cursor, conn_wrapper=None):
        self.cursor = real_cursor
        self.conn_wrapper = conn_wrapper
        self.lastrowid = None

    def execute(self, sql: str, params=None):
        pg_sql = sql.replace("?", "%s")
        upper_sql = pg_sql.strip().upper()
        is_insert = upper_sql.startswith("INSERT INTO") and "RETURNING" not in upper_sql
        if is_insert:
            pg_sql = pg_sql.rstrip(";") + " RETURNING id;"

        def _do_execute(cur):
            if params:
                cur.execute(pg_sql, params)
            else:
                cur.execute(pg_sql)
            if is_insert:
                try:
                    row = cur.fetchone()
                    if row:
                        self.lastrowid = row[0] if isinstance(row, tuple) else row.get("id")
                except Exception:
                    pass

        try:
            _do_execute(self.cursor)
            return self
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as err:
            # Stale / idle connection recovery:
            try:
                if self.conn_wrapper and self.conn_wrapper.conn:
                    self.conn_wrapper.conn.rollback()
            except Exception:
                pass
            
            try:
                fresh_conn_wrapper = get_connection(force_fresh=True)
                if isinstance(fresh_conn_wrapper, PgConnectionWrapper):
                    self.cursor = fresh_conn_wrapper.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    self.conn_wrapper = fresh_conn_wrapper
                    _do_execute(self.cursor)
                    return self
            except Exception:
                pass
            raise err

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return PgRow(row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        if not rows:
            return []
        return [PgRow(r) for r in rows]

    def __iter__(self):
        return iter(self.fetchall())

_PG_POOL = None
_DB_INITIALIZED = False

class PgConnectionWrapper:
    def __init__(self, real_conn, pool=None):
        self.conn = real_conn
        self.pool = pool

    def cursor(self):
        return PgCursorWrapper(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), conn_wrapper=self)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        if self.pool:
            try:
                self.pool.putconn(self.conn)
            except Exception:
                try:
                    self.conn.close()
                except Exception:
                    pass
        else:
            try:
                self.conn.close()
            except Exception:
                pass

def get_connection(force_fresh: bool = False):
    if is_postgres() and PSYCOPG2_AVAILABLE:
        global _PG_POOL
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        if "?" not in url and any(provider in url for provider in ["supabase", "neon", "render", "railway", "pooler"]):
            url += "?sslmode=require"

        if force_fresh and _PG_POOL:
            try:
                _PG_POOL.closeall()
            except Exception:
                pass
            _PG_POOL = None

        for attempt in range(2):
            try:
                if _PG_POOL is None or _PG_POOL.closed:
                    from psycopg2 import pool
                    _PG_POOL = pool.ThreadedConnectionPool(
                        1, 15, url,
                        connect_timeout=10,
                        keepalives=1,
                        keepalives_idle=30,
                        keepalives_interval=10,
                        keepalives_count=5
                    )
                
                real_conn = _PG_POOL.getconn()
                is_alive = False
                try:
                    if real_conn.closed == 0:
                        with real_conn.cursor() as test_cur:
                            test_cur.execute("SELECT 1;")
                        is_alive = True
                except Exception:
                    is_alive = False

                if not is_alive:
                    try:
                        _PG_POOL.putconn(real_conn, close=True)
                    except Exception:
                        pass
                    real_conn = _PG_POOL.getconn()

                return PgConnectionWrapper(real_conn, pool=_PG_POOL)
            except Exception as e:
                if _PG_POOL and not _PG_POOL.closed:
                    try:
                        _PG_POOL.closeall()
                    except Exception:
                        pass
                    _PG_POOL = None
                if attempt == 1:
                    print(f"PostgreSQL connection failed ({e}), falling back to SQLite.")
                    break

        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,)
if PSYCOPG2_AVAILABLE:
    DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg2.IntegrityError)

def init_db():
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    _DB_INITIALIZED = True

    conn = get_connection()
    cursor = conn.cursor()

    if is_postgres():
        # PostgreSQL Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL CHECK(role IN ('student', 'faculty')),
            full_name VARCHAR(150) NOT NULL,
            email VARCHAR(150) DEFAULT '',
            department VARCHAR(150) DEFAULT '',
            college VARCHAR(150) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            faculty_id INTEGER,
            title VARCHAR(255) NOT NULL,
            project_idea TEXT NOT NULL,
            blueprint_json TEXT NOT NULL,
            current_phase INTEGER DEFAULT 1,
            progress_percent REAL DEFAULT 10.0,
            status VARCHAR(50) DEFAULT 'Awaiting Mentor',
            faculty_feedback TEXT DEFAULT '',
            team_members TEXT DEFAULT '',
            supervisor_action_items TEXT DEFAULT '',
            faculty_score INTEGER DEFAULT NULL,
            faculty_score_breakdown TEXT DEFAULT '',
            sign_off_date VARCHAR(50) DEFAULT NULL,
            invite_code VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress_logs (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL,
            week_number INTEGER NOT NULL,
            phase_name VARCHAR(255) NOT NULL,
            tasks_completed TEXT NOT NULL,
            submitted_code TEXT DEFAULT '',
            code_language VARCHAR(50) DEFAULT 'python',
            blockers TEXT DEFAULT '',
            github_link TEXT DEFAULT '',
            ai_feedback TEXT NOT NULL,
            code_audit TEXT DEFAULT '',
            ai_score INTEGER DEFAULT 80,
            faculty_status VARCHAR(50) DEFAULT 'Pending Faculty Review',
            faculty_comment TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()

    else:
        # SQLite Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'faculty')),
            full_name TEXT NOT NULL,
            email TEXT DEFAULT '',
            department TEXT DEFAULT 'Computer Science & Engineering',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            faculty_id INTEGER,
            title TEXT NOT NULL,
            project_idea TEXT NOT NULL,
            blueprint_json TEXT NOT NULL,
            current_phase INTEGER DEFAULT 1,
            progress_percent REAL DEFAULT 0.0,
            status TEXT DEFAULT 'In Progress',
            faculty_feedback TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(faculty_id) REFERENCES users(id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            week_number INTEGER NOT NULL,
            phase_name TEXT NOT NULL,
            tasks_completed TEXT NOT NULL,
            submitted_code TEXT DEFAULT '',
            code_language TEXT DEFAULT 'python',
            blockers TEXT DEFAULT '',
            github_link TEXT DEFAULT '',
            ai_feedback TEXT NOT NULL,
            code_audit TEXT DEFAULT '',
            ai_score INTEGER DEFAULT 80,
            faculty_status TEXT DEFAULT 'Pending Faculty Review',
            faculty_comment TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)

        conn.commit()

        # Safe Schema Migrations (in case SQLite table already existed without new columns)
        cursor.execute("PRAGMA table_info(projects)")
        proj_cols = [r[1] for r in cursor.fetchall()]
        if "faculty_id" not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN faculty_id INTEGER DEFAULT 2")
        if "team_members" not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN team_members TEXT DEFAULT 'Aarav Sharma (21CS045)'")
        if "supervisor_action_items" not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN supervisor_action_items TEXT DEFAULT ''")
        if "faculty_score" not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN faculty_score INTEGER DEFAULT NULL")
        if "faculty_score_breakdown" not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN faculty_score_breakdown TEXT DEFAULT ''")
        if "sign_off_date" not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN sign_off_date TEXT DEFAULT NULL")
        if "invite_code" not in proj_cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN invite_code TEXT")

        cursor.execute("PRAGMA table_info(progress_logs)")
        log_cols = [r[1] for r in cursor.fetchall()]
        if "submitted_code" not in log_cols:
            cursor.execute("ALTER TABLE progress_logs ADD COLUMN submitted_code TEXT DEFAULT ''")
        if "code_language" not in log_cols:
            cursor.execute("ALTER TABLE progress_logs ADD COLUMN code_language TEXT DEFAULT 'python'")
        if "code_audit" not in log_cols:
            cursor.execute("ALTER TABLE progress_logs ADD COLUMN code_audit TEXT DEFAULT ''")
        if "faculty_status" not in log_cols:
            cursor.execute("ALTER TABLE progress_logs ADD COLUMN faculty_status TEXT DEFAULT 'Pending Faculty Review'")
        if "faculty_comment" not in log_cols:
            cursor.execute("ALTER TABLE progress_logs ADD COLUMN faculty_comment TEXT DEFAULT ''")

        cursor.execute("PRAGMA table_info(users)")
        user_cols = [r[1] for r in cursor.fetchall()]
        if "department" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT 'Computer Science & Engineering'")
        if "college" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN college TEXT DEFAULT 'National Institute of Technology'")

        conn.commit()

    # Seed Default Accounts with distinctive colleges
    seed_users = [
        ("student1", "student123", "student", "Aarav Sharma", "aarav.cse@college.edu", "Computer Science & Engineering", "St. Xavier's Institute of Engineering"),
        ("student2", "student123", "student", "Priya Patel", "priya.ai@college.edu", "Artificial Intelligence & Data Science", "Vellore Institute of Technology"),
        ("faculty1", "faculty123", "faculty", "Dr. Ramesh Gupta", "r.gupta@college.edu", "AI & Machine Learning Dept", "National Institute of Technology"),
        ("faculty2", "faculty123", "faculty", "Prof. Sunita Rao", "s.rao@college.edu", "Software Systems & Cloud Dept", "Indian Institute of Science & Tech")
    ]
    for uname, pword, role, fname, email, dept, col in seed_users:
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (uname,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, full_name, email, department, college) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uname, hash_password(pword), role, fname, email, dept, col)
            )
        else:
            # Ensure college is updated for seed accounts
            cursor.execute("UPDATE users SET college = ? WHERE username = ? AND (college IS NULL OR college = '' OR college = 'National Institute of Technology')", (col, uname))

    conn.commit()

    # Backfill invite codes for existing projects
    cursor.execute("SELECT id, invite_code FROM projects")
    for r in cursor.fetchall():
        pid, code = r[0], r[1]
        if not code:
            import random
            new_code = f"PRJ-{random.randint(1000, 9999)}"
            cursor.execute("UPDATE projects SET invite_code = ? WHERE id = ?", (new_code, pid))
    conn.commit()

    # Seed Demo Project for student1 if no projects exist
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM users WHERE username = 'student1'")
        s_row = cursor.fetchone()
        cursor.execute("SELECT id FROM users WHERE username = 'faculty1'")
        f_row = cursor.fetchone()
        
        if s_row and f_row:
            s_id = s_row[0]
            f_id = f_row[0]
            demo_blueprint = {
                "mentor_report": "### 🏆 1. Executive Evaluation & Score Potential\n- **Overall Feasibility Score:** 92 / 100\n- **Innovation Rating:** 88 / 100\n- **Verdict:** Approved for Academic Capstone. Strong alignment with generative AI enterprise systems.\n\n### 🎯 2. Approved Architecture & Core Milestones\n- Streamlit UI communicating with FastAPI backend.\n- LangChain / Groq RAG pipeline with ChromaDB vector store.\n- Dockerized deployment ready for cloud hosting.\n\n### ❓ 3. Viva Voce Q&A Preparation\n- **Q1:** What chunking strategy did you use and why?\n  *Answer:* Recursive character text splitter with chunk size of 500 and overlap 50 to maintain semantic coherence.\n- **Q2:** How do you mitigate hallucinations?\n  *Answer:* Strict RAG context constraints with prompt guardrails and source attribution.",
                "idea": "### 1. Academic Suitability\nStrong capstone project showcasing NLP, Vector Search, and LLM Orchestration.\n\n### 2. Core Problem & Beneficiaries\nAutomates Tier-1 customer support queries with 24/7 responsiveness for e-commerce and SaaS platforms.\n\n### 3. Innovation & USP\nHybrid keyword-semantic retrieval with hallucination guardrails.\n\n### 4. Feasibility Scorecard\n- Feasibility: High\n- Difficulty: Intermediate\n- Innovation: High\n- Estimated Duration: 8 Weeks\n- Recommendation: Proceed with project",
                "scope": "### 1. Primary Objectives\n- Automate 75%+ of repetitive customer queries.\n- Achieve sub-2s response latency using Groq.\n- Integrate source document citations.\n\n### 2. Top 5 Core Features\n1. Multi-turn context memory\n2. Semantic vector search over company knowledge base\n3. Source citation highlights\n4. Analytics dashboard for support agents\n5. Escalation trigger for human agent takeover",
                "technology": "### 1. Frontend\nStreamlit for intuitive, fast academic UI prototyping.\n\n### 2. Backend\nFastAPI for asynchronous, high-throughput endpoints.\n\n### 3. AI / ML Framework\nGroq SDK with Qwen/Llama models & LangChain for orchestration.\n\n### 4. Database\nChromaDB for vector storage and SQLite for user sessions.\n\n### 5. Deployment\nDocker containerization on Render / Hugging Face Spaces.",
                "planning": "### 📅 Phase 1: Problem Identification & SRS (Week 1)\n### 📅 Phase 2: Knowledge Base Ingestion & Chunking (Week 2)\n### 📅 Phase 3: Vector Embeddings & ChromaDB Setup (Week 3)\n### 📅 Phase 4: LangChain & Groq API Integration (Week 4)\n### 📅 Phase 5: Streamlit Frontend & Multi-turn Chat (Week 5)\n### 📅 Phase 6: System Evaluation & Retrieval Benchmarking (Week 6)\n### 📅 Phase 7: Docker Containerization & Deployment (Week 7)\n### 📅 Phase 8: Final Thesis, PPT & Viva Defense (Week 8)",
                "risks": "### ⚠️ Risk 1: Dataset Quality\n- Mitigation: Curated e-commerce FAQ dataset from Kaggle + synthetic queries.\n### ⚠️ Risk 2: API Rate Limits\n- Mitigation: Groq high-speed free tier with local token caching.\n### ⚠️ Risk 3: Hallucination\n- Mitigation: Strict prompt boundaries: 'Answer ONLY based on the context below.'",
                "documentation": "### 1. Formal Abstract\nCustomer service efficiency directly impacts user satisfaction in modern e-commerce. This project presents an intelligent Retrieval-Augmented Generation (RAG) customer support conversational agent built using high-speed LLM inference and vector search. Results demonstrate a 78% query resolution rate with sub-1.5 second latency.\n\n### 4. System Architecture Diagram\n```mermaid\ngraph TD\n    Customer[Customer / Student] --> UI[Streamlit Chat UI]\n    UI --> API[FastAPI Controller]\n    API --> Retriever[Vector Retriever / ChromaDB]\n    API --> LLM[Groq AI Agent Pipeline]\n    LLM --> Response[Verified Answer with Citations]\n```"
            }

            cursor.execute("""
                INSERT INTO projects (user_id, faculty_id, title, project_idea, blueprint_json, current_phase, progress_percent, status, faculty_feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s_id,
                None,
                "AI-Powered Customer Support Chatbot",
                "I want to build an AI-powered customer support chatbot using Generative AI and vector search to answer customer queries automatically.",
                json.dumps(demo_blueprint),
                4,
                48.0,
                "Awaiting Mentor",
                ""
            ))
            demo_pid = cursor.lastrowid

            demo_code = '''import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="Customer Support Chatbot RAG")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class QueryRequest(BaseModel):
    user_query: str
    session_id: str

@app.post("/api/chat")
async def chat_endpoint(req: QueryRequest):
    if not req.user_query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Retrieve top documents from vector store (ChromaDB mock)
    retrieved_context = "Return policy: 30 days full refund on undamaged items."
    
    prompt = f"Context: {retrieved_context}\\nQuery: {req.user_query}\\nAnswer:"
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return {"reply": response.choices[0].message.content, "source": "FAQ_Docs_v1"}
'''

            cursor.execute("""
                INSERT INTO progress_logs (
                    project_id, week_number, phase_name, tasks_completed,
                    submitted_code, code_language, blockers, github_link,
                    ai_feedback, code_audit, ai_score, faculty_status, faculty_comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                demo_pid,
                3,
                "Phase 3: System Architecture & UML Design",
                "Designed FastAPI asynchronous endpoints and integrated Groq SDK with context injection.",
                demo_code,
                "python",
                "Optimizing cold start latency for vector similarity search.",
                "https://github.com/aarav-sharma/ai-support-chatbot",
                "### Milestone Verification: PASSED\nFastAPI route handles query validation, injection, and error catching effectively.",
                "### 🔍 AI Code Quality Audit (Score: 92/100)\n- **Modularity:** Clean separation with Pydantic request models.\n- **Error Handling:** 400 Bad Request exception implemented.\n- **Security:** Groq API key loaded from environment variable.\n- **Improvement Tip:** Add rate-limiting middleware and async database session management.",
                92,
                "Pending Faculty Review",
                ""
            ))

    conn.commit()
    conn.close()

def generate_unique_invite_code(conn=None) -> str:
    import random
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    cursor = conn.cursor()
    while True:
        num = random.randint(1000, 9999)
        code = f"PRJ-{num}"
        cursor.execute("SELECT COUNT(*) FROM projects WHERE invite_code = ?", (code,))
        if cursor.fetchone()[0] == 0:
            if should_close:
                conn.close()
            return code

def register_user(username: str, password: str, role: str, full_name: str, email: str = "", department: str = "", college: str = "") -> tuple:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        clean_uname = username.strip().lower()
        clean_email = email.strip().lower()

        cursor.execute("SELECT id FROM users WHERE LOWER(username) = ?", (clean_uname,))
        if cursor.fetchone():
            return False, f"The username '{clean_uname}' is already registered. Please choose another username or switch to 'Sign In'."

        if clean_email:
            cursor.execute("SELECT id, username FROM users WHERE LOWER(email) = ?", (clean_email,))
            row = cursor.fetchone()
            if row:
                existing_uname = row["username"]
                return False, f"The email '{clean_email}' is already registered (Username: '{existing_uname}'). You already have an account! Please switch to the 'Sign In' tab to log in."

        cursor.execute(
            "INSERT INTO users (username, password_hash, role, full_name, email, department, college) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (clean_uname, hash_password(password), role, full_name.strip(), clean_email, department.strip(), college.strip())
        )
        conn.commit()
        return True, "Account created successfully! Switch to the 'Sign In' tab to log in."
    except DB_INTEGRITY_ERRORS:
        return False, "This username or email is already registered."
    finally:
        conn.close()

def authenticate_user(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates user by either username OR email address with automatic reconnection and fallback."""
    if not identifier or not password:
        return None
    clean_id = identifier.strip().lower()
    hashed_pwd = hash_password(password.strip())

    for attempt in range(2):
        try:
            conn = get_connection(force_fresh=(attempt > 0))
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, role, full_name, email, department, college 
                FROM users 
                WHERE (LOWER(username) = ? OR LOWER(email) = ?) 
                  AND password_hash = ?
                """,
                (clean_id, clean_id, hashed_pwd)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)
            return None
        except Exception:
            if attempt == 0:
                continue
            try:
                fb_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                fb_conn.row_factory = sqlite3.Row
                fb_cur = fb_conn.cursor()
                fb_cur.execute(
                    """
                    SELECT id, username, role, full_name, email, department, college 
                    FROM users 
                    WHERE (LOWER(username) = ? OR LOWER(email) = ?) 
                      AND password_hash = ?
                    """,
                    (clean_id, clean_id, hashed_pwd)
                )
                fb_row = fb_cur.fetchone()
                fb_conn.close()
                if fb_row:
                    return dict(fb_row)
            except Exception:
                pass
            return None
    return None

def get_faculty_users() -> List[Dict[str, Any]]:
    """Returns list of all registered faculty mentors."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, department, email, college FROM users WHERE role = 'faculty' ORDER BY full_name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_project(user_id: int, title: str, project_idea: str, faculty_id: Optional[int], blueprint: Dict[str, Any], team_members: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    invite_code = generate_unique_invite_code(conn)
    initial_status = "Under Review" if faculty_id else "Awaiting Mentor"
    cursor.execute(
        """
        INSERT INTO projects (user_id, faculty_id, title, project_idea, blueprint_json, current_phase, progress_percent, status, team_members, invite_code)
        VALUES (?, ?, ?, ?, ?, 1, 10.0, ?, ?, ?)
        """,
        (user_id, faculty_id, title, project_idea, json.dumps(blueprint), initial_status, team_members.strip() if team_members.strip() else "Student Team", invite_code)
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id

def get_project_by_invite_code(invite_code: str) -> Optional[Dict[str, Any]]:
    code = invite_code.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u.full_name as student_name, u.email as student_email, u.department as student_dept, u.college as student_college,
               f.full_name as faculty_name, f.email as faculty_email, f.college as faculty_college
        FROM projects p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN users f ON p.faculty_id = f.id
        WHERE UPPER(p.invite_code) = ?
    """, (code,))
    row = cursor.fetchone()
    conn.close()
    if row:
        p = dict(row)
        try:
            p["blueprint"] = json.loads(p["blueprint_json"])
        except Exception:
            p["blueprint"] = {}
        return p
    return None

def link_faculty_to_project_by_code(faculty_id: int, invite_code: str) -> tuple:
    code = invite_code.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, faculty_id FROM projects WHERE UPPER(invite_code) = ?", (code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "Invalid invite code. No project found with this code."

    pid, title, current_fac = row["id"], row["title"], row["faculty_id"]
    if current_fac == faculty_id:
        conn.close()
        return False, f"You are already connected as the supervisor for '{title}'."

    cursor.execute("""
        UPDATE projects 
        SET faculty_id = ?, status = 'In Progress', updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (faculty_id, pid))
    conn.commit()
    conn.close()
    return True, f"Successfully linked as supervisor for '{title}'!"

def delete_project(project_id: int, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM progress_logs WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM chat_messages WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def update_project_faculty(project_id: int, faculty_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET faculty_id = ?, status = 'In Progress', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (faculty_id, project_id))
    conn.commit()
    conn.close()

def get_student_projects(user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, f.full_name as faculty_name, f.department as faculty_dept, f.email as faculty_email, f.college as faculty_college
        FROM projects p 
        LEFT JOIN users f ON p.faculty_id = f.id
        WHERE p.user_id = ? 
        ORDER BY p.updated_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    projects = []
    for r in rows:
        p = dict(r)
        try:
            p["blueprint"] = json.loads(p["blueprint_json"])
        except Exception:
            p["blueprint"] = {}
        projects.append(p)
    return projects

def get_student_project_list(user_id: int) -> List[Dict[str, Any]]:
    """Ultra-fast lightweight fetch of project IDs and titles for dropdown menus without parsing heavy JSON."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM projects WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r["id"], "title": r["title"]} for r in rows]

def get_all_projects_for_faculty(faculty_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if faculty_id:
        cursor.execute("""
            SELECT p.*, u.full_name as student_name, u.email as student_email, u.department as student_dept, u.college as student_college,
                   f.full_name as faculty_name, f.college as faculty_college
            FROM projects p 
            JOIN users u ON p.user_id = u.id 
            LEFT JOIN users f ON p.faculty_id = f.id
            WHERE p.faculty_id = ?
            ORDER BY p.updated_at DESC
        """, (faculty_id,))
    else:
        cursor.execute("""
            SELECT p.*, u.full_name as student_name, u.email as student_email, u.department as student_dept, u.college as student_college,
                   f.full_name as faculty_name, f.college as faculty_college
            FROM projects p 
            JOIN users u ON p.user_id = u.id 
            LEFT JOIN users f ON p.faculty_id = f.id
            ORDER BY p.updated_at DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    projects = []
    for r in rows:
        p = dict(r)
        try:
            p["blueprint"] = json.loads(p["blueprint_json"])
        except Exception:
            p["blueprint"] = {}
        projects.append(p)
    return projects

def get_project_by_id(project_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u.full_name as student_name, u.email as student_email, u.department as student_dept, u.college as student_college,
               f.full_name as faculty_name, f.email as faculty_email, f.department as faculty_dept, f.college as faculty_college
        FROM projects p 
        JOIN users u ON p.user_id = u.id 
        LEFT JOIN users f ON p.faculty_id = f.id
        WHERE p.id = ?
    """, (project_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        p = dict(row)
        try:
            p["blueprint"] = json.loads(p["blueprint_json"])
        except Exception:
            p["blueprint"] = {}
        return p
    return None

def update_project_progress(project_id: int, progress_percent: float, current_phase: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE projects 
        SET progress_percent = ?, current_phase = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (progress_percent, current_phase, project_id))
    conn.commit()
    conn.close()

def update_faculty_feedback(project_id: int, feedback: str, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE projects 
        SET faculty_feedback = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (feedback, status, project_id))
    conn.commit()
    conn.close()

def update_faculty_evaluation(
    project_id: int,
    feedback: str,
    status: str,
    action_items: str = "",
    faculty_score: Optional[int] = None,
    score_breakdown: str = "",
    grant_sign_off: bool = False
):
    conn = get_connection()
    cursor = conn.cursor()
    sign_off_stamp = datetime.now().strftime("%B %d, %Y") if grant_sign_off else None
    
    if grant_sign_off:
        cursor.execute("""
            UPDATE projects 
            SET faculty_feedback = ?, status = 'Approved', supervisor_action_items = ?,
                faculty_score = ?, faculty_score_breakdown = ?, sign_off_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (feedback, action_items, faculty_score, score_breakdown, sign_off_stamp, project_id))
    else:
        cursor.execute("""
            UPDATE projects 
            SET faculty_feedback = ?, status = ?, supervisor_action_items = ?,
                faculty_score = ?, faculty_score_breakdown = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (feedback, status, action_items, faculty_score, score_breakdown, project_id))

    conn.commit()
    conn.close()

def update_project_team(project_id: int, team_members: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET team_members = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (team_members.strip(), project_id))
    conn.commit()
    conn.close()

def add_progress_log(
    project_id: int,
    week_number: int,
    phase_name: str,
    tasks_completed: str,
    submitted_code: str,
    code_language: str,
    blockers: str,
    github_link: str,
    ai_feedback: str,
    code_audit: str,
    ai_score: int
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO progress_logs (
            project_id, week_number, phase_name, tasks_completed,
            submitted_code, code_language, blockers, github_link,
            ai_feedback, code_audit, ai_score, faculty_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending Faculty Review')
    """, (
        project_id, week_number, phase_name, tasks_completed,
        submitted_code, code_language, blockers, github_link,
        ai_feedback, code_audit, ai_score
    ))
    conn.commit()
    conn.close()

def update_progress_log_faculty_review(log_id: int, faculty_status: str, faculty_comment: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE progress_logs 
        SET faculty_status = ?, faculty_comment = ?
        WHERE id = ?
    """, (faculty_status, faculty_comment, log_id))
    conn.commit()
    conn.close()

def get_progress_logs(project_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM progress_logs WHERE project_id = ? ORDER BY week_number ASC, created_at ASC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_chat_message(project_id: int, user_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages (project_id, user_id, role, content)
        VALUES (?, ?, ?, ?)
    """, (project_id, user_id, role, content))
    conn.commit()
    conn.close()

def get_chat_messages(project_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM chat_messages WHERE project_id = ? ORDER BY created_at ASC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Auto initialize database on module import
init_db()
