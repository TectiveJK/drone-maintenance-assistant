from pathlib import Path
import os
import sqlite3
from datetime import datetime

APP_DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "drone-maintenance-assistant"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DATA_DIR / "drone_maintenance.db"
SHARED_TEST_DAY_DIR = Path.home() / "DroneTestDay"


def shared_test_day_dir():
    SHARED_TEST_DAY_DIR.mkdir(parents=True, exist_ok=True)
    return SHARED_TEST_DAY_DIR

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def _columns(con, table):
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}

def _add_column(con, table, column, definition):
    if column not in _columns(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    con = connect()
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript('''
    CREATE TABLE IF NOT EXISTS drones (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, manufacturer TEXT, model TEXT, serial_number TEXT, firmware TEXT, equipment TEXT, flight_hours REAL DEFAULT 0, flight_count INTEGER DEFAULT 0, notes TEXT, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS inspections (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER NOT NULL, inspection_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PASS', notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS inspection_items (id INTEGER PRIMARY KEY AUTOINCREMENT, inspection_id INTEGER NOT NULL, item_name TEXT NOT NULL, result TEXT NOT NULL DEFAULT 'N/A', notes TEXT, FOREIGN KEY(inspection_id) REFERENCES inspections(id));
    CREATE TABLE IF NOT EXISTS maintenance_issues (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER NOT NULL, source TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS batteries (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER, battery_id TEXT NOT NULL, cycles INTEGER DEFAULT 0, voltage TEXT, health TEXT, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS maintenance_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER NOT NULL, task TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'NORMAL', status TEXT NOT NULL DEFAULT 'OPEN', due_date TEXT, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER NOT NULL, title TEXT NOT NULL, severity TEXT NOT NULL, description TEXT, action_taken TEXT, status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS flight_test_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, report_id TEXT, project TEXT, test_id TEXT, aircraft TEXT, source_file TEXT, report_json TEXT NOT NULL, imported_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS retrieved_flight_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER, file_name TEXT NOT NULL, local_path TEXT NOT NULL, source TEXT, retrieved_at TEXT NOT NULL);
    ''')

    # Migrate databases created by earlier versions of the application.
    _add_column(con, "drones", "equipment", "TEXT")
    _add_column(con, "drones", "firmware", "TEXT")
    _add_column(con, "drones", "flight_hours", "REAL DEFAULT 0")
    _add_column(con, "drones", "flight_count", "INTEGER DEFAULT 0")
    _add_column(con, "drones", "notes", "TEXT")
    _add_column(con, "inspections", "status", "TEXT NOT NULL DEFAULT 'PASS'")
    _add_column(con, "inspections", "notes", "TEXT")
    _add_column(con, "inspection_items", "result", "TEXT NOT NULL DEFAULT 'N/A'")
    _add_column(con, "inspection_items", "notes", "TEXT")
    _add_column(con, "maintenance_issues", "status", "TEXT NOT NULL DEFAULT 'OPEN'")
    _add_column(con, "maintenance_issues", "created_at", "TEXT")
    _add_column(con, "batteries", "cycles", "INTEGER DEFAULT 0")
    _add_column(con, "batteries", "voltage", "TEXT")
    _add_column(con, "batteries", "health", "TEXT")
    _add_column(con, "batteries", "notes", "TEXT")
    _add_column(con, "maintenance_tasks", "priority", "TEXT NOT NULL DEFAULT 'NORMAL'")
    _add_column(con, "maintenance_tasks", "status", "TEXT NOT NULL DEFAULT 'OPEN'")
    _add_column(con, "maintenance_tasks", "due_date", "TEXT")
    _add_column(con, "maintenance_tasks", "notes", "TEXT")
    _add_column(con, "incidents", "severity", "TEXT NOT NULL DEFAULT 'MEDIUM'")
    _add_column(con, "incidents", "description", "TEXT")
    _add_column(con, "incidents", "action_taken", "TEXT")
    _add_column(con, "incidents", "status", "TEXT NOT NULL DEFAULT 'OPEN'")

    # Existing rows may contain NULLs after migration; normalize values used by reports/UI.
    con.execute("UPDATE inspections SET status='PASS' WHERE status IS NULL OR status=''")
    con.execute("UPDATE inspection_items SET result='N/A' WHERE result IS NULL OR result=''")
    con.execute("UPDATE maintenance_issues SET status='OPEN' WHERE status IS NULL OR status=''")
    con.execute("UPDATE batteries SET cycles=0 WHERE cycles IS NULL")
    con.execute("UPDATE maintenance_tasks SET priority='NORMAL' WHERE priority IS NULL OR priority=''")
    con.execute("UPDATE maintenance_tasks SET status='OPEN' WHERE status IS NULL OR status=''")
    con.execute("UPDATE incidents SET severity='MEDIUM' WHERE severity IS NULL OR severity=''")
    con.execute("UPDATE incidents SET status='OPEN' WHERE status IS NULL OR status=''")
    con.commit()
    con.close()

def now():
    return datetime.now().isoformat(timespec="seconds")
