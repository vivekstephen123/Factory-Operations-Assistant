"""
Database module for Enterprise SQL & Factory Operations Assistant.
Implements the exact MySQL 8.0 DDL schema:
- machines (machine_id, machine_name, location, status, created_at)
- downtime (downtime_id, machine_id, date, duration_hours, reason)
- maintenance_requests (request_id, machine_id, description, priority, status, created_at)

Supports:
1. MySQL 8.0+ via mysql-connector-python (factory_ops_db)
2. SQLite (local zero-configuration mirror with identical schema and 460 records)
"""

import os
import sqlite3
import datetime
from typing import List, Dict, Any, Tuple

# Base paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "factory_operations.db")
SAMPLE_SQL_PATH = os.path.join(DATA_DIR, "sample_database.sql")

# Fallback paths for legacy structure
FALLBACK_SCHEMA_PATH = os.path.join(PROJECT_ROOT, "database", "schema.sql")
FALLBACK_SEED_PATH = os.path.join(PROJECT_ROOT, "database", "seed_data.sql")
FALLBACK_DB_PATH = os.path.join(PROJECT_ROOT, "database", "factory_operations.db")

# MySQL Environment configurations
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "factory_ops_db")


def is_mysql_available() -> bool:
    """Checks whether the MySQL server is reachable with the provided credentials."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            connection_timeout=2
        )
        conn.close()
        return True
    except Exception:
        return False


def get_active_engine_name() -> str:
    """Returns the name of the currently active storage backend."""
    return "MySQL 8.0 (Production)" if is_mysql_available() else "SQLite 3 (Local Mirror)"


def get_connection():
    """Returns a database connection for MySQL or SQLite."""
    if is_mysql_available():
        import mysql.connector
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
    else:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn


def _clean_sql_statement(raw_stmt: str) -> str:
    """Strips comments (-- and /* */) and whitespace from an SQL statement."""
    lines = []
    for line in raw_stmt.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("--") or trimmed.startswith("/*"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def init_database(force_reseed: bool = False):
    """Initializes the database schema and loads initial records."""
    os.makedirs(DATA_DIR, exist_ok=True)
    using_mysql = is_mysql_available()

    if using_mysql:
        import mysql.connector
        admin_conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        admin_cursor = admin_conn.cursor()
        admin_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        admin_conn.commit()
        admin_conn.close()

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        if force_reseed:
            cursor.execute("DROP TABLE IF EXISTS maintenance_requests;")
            cursor.execute("DROP TABLE IF EXISTS downtime;")
            cursor.execute("DROP TABLE IF EXISTS machines;")
            conn.commit()

        # Load schema / sample data
        sql_file = SAMPLE_SQL_PATH if os.path.exists(SAMPLE_SQL_PATH) else FALLBACK_SCHEMA_PATH
        if os.path.exists(sql_file):
            with open(sql_file, "r", encoding="utf-8") as f:
                content = f.read()

            for raw_stmt in content.split(";"):
                stmt = _clean_sql_statement(raw_stmt)
                if not stmt:
                    continue
                upper = stmt.upper()
                if upper.startswith("USE ") or upper.startswith("CREATE DATABASE"):
                    continue
                cursor.execute(stmt)
            conn.commit()

        cursor.execute("SELECT COUNT(*) as cnt FROM machines;")
        count = cursor.fetchone()["cnt"]

        if count == 0:
            _seed_data(cursor, is_mysql=True)
            conn.commit()

        conn.close()
        print(f"[Database] Initialized MySQL database '{MYSQL_DATABASE}' successfully.")

    else:
        conn = get_connection()
        cursor = conn.cursor()

        if force_reseed:
            cursor.execute("DROP TABLE IF EXISTS maintenance_requests;")
            cursor.execute("DROP TABLE IF EXISTS downtime;")
            cursor.execute("DROP TABLE IF EXISTS machines;")
            conn.commit()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            machine_id TEXT PRIMARY KEY,
            machine_name TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPERATIONAL',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS downtime (
            downtime_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            date TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            reason TEXT NOT NULL,
            FOREIGN KEY (machine_id) REFERENCES machines (machine_id) ON DELETE CASCADE ON UPDATE CASCADE
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_downtime_machine_date ON downtime (machine_id, date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_downtime_date ON downtime (date);")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'MEDIUM',
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (machine_id) REFERENCES machines (machine_id) ON DELETE CASCADE ON UPDATE CASCADE
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_machine ON maintenance_requests (machine_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_status ON maintenance_requests (status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_created_at ON maintenance_requests (created_at);")

        cursor.execute("SELECT COUNT(*) as cnt FROM machines")
        count = cursor.fetchone()["cnt"]

        if count == 0:
            _seed_data(cursor, is_mysql=False)
            conn.commit()

        conn.close()
        print(f"[Database] Initialized SQLite mirror database '{SQLITE_DB_PATH}' successfully.")


def _seed_data(cursor, is_mysql: bool):
    """Populates initial factory data (120 machines, 180 downtime, 160 requests)."""
    seed_file = SAMPLE_SQL_PATH if os.path.exists(SAMPLE_SQL_PATH) else FALLBACK_SEED_PATH
    if not os.path.exists(seed_file):
        return

    with open(seed_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    statements = [s.strip() for s in sql_content.split(";") if s.strip()]
    for raw_stmt in statements:
        stmt = _clean_sql_statement(raw_stmt)
        if not stmt:
            continue
        upper = stmt.upper()
        if upper.startswith("USE ") or upper == "USE" or upper.startswith("CREATE DATABASE") or upper.startswith("CREATE TABLE") or upper.startswith("DROP TABLE"):
            if not is_mysql and (upper.startswith("CREATE TABLE") or upper.startswith("DROP TABLE")):
                # In SQLite, schema was already created above
                continue
            if upper.startswith("USE ") or upper.startswith("CREATE DATABASE"):
                continue

        if not is_mysql:
            if "FOREIGN_KEY_CHECKS" in upper:
                continue
            if "TRUNCATE TABLE" in upper:
                words = stmt.split()
                table_name = words[-1].strip(";").strip()
                cursor.execute(f"DELETE FROM {table_name}")
                continue
        cursor.execute(stmt)


def execute_sql_query(sql_query: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Executes a SELECT SQL query safely.
    Returns (rows, error_message).
    """
    stripped = sql_query.strip().upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        return [], "Safety rejection: Only read-only SELECT queries are allowed via query_database."

    try:
        conn = get_connection()
        if is_mysql_available():
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql_query)
            rows = cursor.fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows, ""
    except Exception as e:
        return [], str(e)


def insert_maintenance_record(machine_id: str, description: str, priority: str = "HIGH") -> Tuple[bool, str]:
    """
    Inserts a newly approved maintenance request record.
    Returns (success, message).
    """
    priority = priority.upper()
    valid_priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if priority not in valid_priorities:
        priority = "HIGH"

    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if is_mysql_available():
            query = """
            INSERT INTO maintenance_requests (machine_id, description, priority, status, created_at)
            VALUES (%s, %s, %s, %s, %s);
            """
            cursor.execute(query, (machine_id, description, priority, "PENDING", now_iso))
            conn.commit()
            inserted_id = cursor.lastrowid
        else:
            query = """
            INSERT INTO maintenance_requests (machine_id, description, priority, status, created_at)
            VALUES (?, ?, ?, ?, ?);
            """
            cursor.execute(query, (machine_id, description, priority, "PENDING", now_iso))
            conn.commit()
            inserted_id = cursor.lastrowid

        conn.close()
        return True, f"Maintenance request #{inserted_id} successfully created for machine {machine_id} (Priority: {priority})."
    except Exception as e:
        return False, f"Failed to insert maintenance request: {str(e)}"


def get_all_records(table_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Returns recent records from a specified table for auditing and UI display."""
    allowed = ["machines", "downtime", "maintenance_requests"]
    if table_name not in allowed:
        return []

    try:
        conn = get_connection()
        if is_mysql_available():
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
            rows = cursor.fetchall()
        else:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
            rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []
