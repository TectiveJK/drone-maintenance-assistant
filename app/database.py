from pathlib import Path
import os
import sqlite3
from datetime import datetime

APP_DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "drone-maintenance-assistant"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DATA_DIR / "drone_maintenance.db"

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = connect()
    con.executescript('''
    CREATE TABLE IF NOT EXISTS drones (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, manufacturer TEXT, model TEXT, serial_number TEXT, firmware TEXT, equipment TEXT, flight_hours REAL DEFAULT 0, flight_count INTEGER DEFAULT 0, notes TEXT, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS inspections (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER NOT NULL, inspection_type TEXT NOT NULL, status TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS inspection_items (id INTEGER PRIMARY KEY AUTOINCREMENT, inspection_id INTEGER NOT NULL, item_name TEXT NOT NULL, result TEXT NOT NULL, notes TEXT, FOREIGN KEY(inspection_id) REFERENCES inspections(id));
    CREATE TABLE IF NOT EXISTS maintenance_issues (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER NOT NULL, source TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS batteries (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER, battery_id TEXT NOT NULL, cycles INTEGER DEFAULT 0, voltage TEXT, health TEXT, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS maintenance_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER NOT NULL, task TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'NORMAL', status TEXT NOT NULL DEFAULT 'OPEN', due_date TEXT, notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, drone_id INTEGER NOT NULL, title TEXT NOT NULL, severity TEXT NOT NULL, description TEXT, action_taken TEXT, status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL, FOREIGN KEY(drone_id) REFERENCES drones(id));
    ''')
    columns = {row[1] for row in con.execute("PRAGMA table_info(incidents)").fetchall()}
    if "status" not in columns:
        con.execute("ALTER TABLE incidents ADD COLUMN status TEXT NOT NULL DEFAULT 'OPEN'")
    con.commit()
    con.close()

def now():
    return datetime.now().isoformat(timespec="seconds")
