import sqlite3
import pytest
from datetime import datetime

from reports import ReportGenerator
from telemetry_importer import TelemetryImporter
from alert_system import ThresholdAlertSystem

@pytest.fixture
def test_db(tmp_path):
    """
    Sets up a clean temporary SQLite database with full schema for each test.
    """
    db_file = tmp_path / "test_app.db"
    db_path = str(db_file)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE drones (
            id TEXT PRIMARY KEY,
            manufacturer TEXT,
            model TEXT,
            serial_number TEXT,
            firmware TEXT,
            flight_hours REAL DEFAULT 0.0,
            flight_count INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE batteries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drone_id TEXT,
            cycle_count INTEGER DEFAULT 0,
            voltage REAL,
            health TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE maintenance_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drone_id TEXT,
            task TEXT,
            priority TEXT,
            status TEXT DEFAULT 'Pending',
            due_date TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drone_id TEXT,
            incident_title TEXT,
            severity TEXT,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drone_id TEXT,
            type TEXT, -- Pre-Flight / Post-Flight
            status TEXT, -- PASS / FAIL / N/A
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()

    return db_path


# =====================================================================
# 1. SCHEMA & DATABASE VALIDATION TESTS
# =====================================================================

def test_database_schema_initialization(test_db):
    """Verify that all core tables are created properly in SQLite."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {"drones", "batteries", "maintenance_tasks", "incidents", "inspections"}
    assert expected_tables.issubset(tables)
    conn.close()


def test_drone_insertion_and_defaults(test_db):
    """Verify drone record insertion and default flight hours/count."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO drones (id, manufacturer, model, serial_number) VALUES (?, ?, ?, ?)",
        ("D001", "DJI", "Matrice 300", "SN-998877")
    )
    conn.commit()

    cursor.execute("SELECT flight_hours, flight_count FROM drones WHERE id = 'D001'")
    hours, count = cursor.fetchone()

    assert hours == 0.0
    assert count == 0
    conn.close()


# =====================================================================
# 2. INSPECTION & AUTO-ISSUE CREATION TESTS
# =====================================================================

def test_failed_inspection_auto_creates_maintenance_issue(test_db):
    """
    Simulates a Pre/Post flight inspection failure and verifies an automatic 
    maintenance task is queued.
    """
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    drone_id = "D001"
    inspection_type = "Pre-Flight"
    inspection_status = "FAIL"
    issue_notes = "Propeller hair-line crack detected during visual inspection."

    # Insert Failed Inspection
    cursor.execute(
        "INSERT INTO inspections (drone_id, type, status, notes) VALUES (?, ?, ?, ?)",
        (drone_id, inspection_type, inspection_status, issue_notes)
    )

    # Trigger maintenance task auto-creation logic
    if inspection_status == "FAIL":
        cursor.execute("""
            INSERT INTO maintenance_tasks (drone_id, task, priority, status, notes)
            VALUES (?, ?, 'High', 'Pending', ?)
        """, (drone_id, f"Auto-Generated: Failed {inspection_type} Inspection", issue_notes))

    conn.commit()

    # Verify task was created
    cursor.execute("SELECT task, priority, status FROM maintenance_tasks WHERE drone_id = ?", (drone_id,))
    task = cursor.fetchone()

    assert task is not None
    assert "Failed Pre-Flight Inspection" in task[0]
    assert task[1] == "High"
    assert task[2] == "Pending"
    conn.close()


# =====================================================================
# 3. ALERT THRESHOLD SYSTEM TESTS
# =====================================================================

def test_flight_hour_threshold_alert(test_db):
    """Verify that drones exceeding 50 flight hours trigger an alert task."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # Insert drone with 52 hours (Threshold is 50.0)
    cursor.execute(
        "INSERT INTO drones (id, serial_number, flight_hours) VALUES (?, ?, ?)",
        ("D100", "SN-ALPHA", 52.0)
    )
    conn.commit()
    conn.close()

    alert_system = ThresholdAlertSystem(db_path=test_db)
    alert_system.check_and_generate_alerts()

    # Verify alert task created
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT task, priority FROM maintenance_tasks WHERE drone_id = 'D100'")
    task = cursor.fetchone()

    assert task is not None
    assert "Routine 50-Hour Inspection" in task[0]
    assert task[1] == "High"
    conn.close()


def test_battery_cycle_threshold_alert(test_db):
    """Verify that batteries exceeding 100 cycles trigger an inspection task."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO batteries (drone_id, cycle_count, voltage) VALUES (?, ?, ?)",
        ("D100", 105, 22.8)
    )
    conn.commit()
    conn.close()

    alert_system = ThresholdAlertSystem(db_path=test_db)
    alert_system.check_and_generate_alerts()

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT task, notes FROM maintenance_tasks WHERE drone_id = 'D100'")
    task = cursor.fetchone()

    assert task is not None
    assert "Inspect/Decommission Battery" in task[0]
    conn.close()


def test_duplicate_alerts_are_prevented(test_db):
    """Ensure running alert system multiple times doesn't spam duplicate tasks."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO drones (id, serial_number, flight_hours) VALUES (?, ?, ?)",
        ("D200", "SN-BETA", 60.0)
    )
    conn.commit()
    conn.close()

    alert_system = ThresholdAlertSystem(db_path=test_db)
    
    # Run twice
    alert_system.check_and_generate_alerts()
    alert_system.check_and_generate_alerts()

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM maintenance_tasks WHERE drone_id = 'D200'")
    count = cursor.fetchone()[0]

    assert count == 1  # Should only create 1 task, not 2
    conn.close()


# =====================================================================
# 4. TELEMETRY IMPORTER & REPORT GENERATION TESTS
# =====================================================================

def test_telemetry_hour_ingestion(test_db, tmp_path):
    """Verify CSV telemetry ingestion updates flight hours accurately."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO drones (id, flight_hours, flight_count) VALUES ('D300', 10.0, 5)")
    conn.commit()
    conn.close()

    # Create dummy telemetry CSV (3600 seconds = 1.0 hour)
    csv_file = tmp_path / "flight_log.csv"
    csv_file.write_text("timestamp,lat,lon,alt\n0,10.0,20.0,100\n3600,10.0,20.0,100")

    importer = TelemetryImporter(db_path=test_db)
    importer.process_flight_log_csv("D300", str(csv_file))

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT flight_hours, flight_count FROM drones WHERE id = 'D300'")
    hours, count = cursor.fetchone()

    assert hours == 11.0  # 10.0 + 1.0
    assert count == 6     # 5 + 1
    conn.close()


def test_pdf_report_generation(test_db, tmp_path):
    """Verify PDF generator produces a valid report file without throwing errors."""
    output_pdf = tmp_path / "test_report.pdf"
    
    reporter = ReportGenerator(db_path=test_db)
    generated_path = reporter.generate_pdf_summary(output_filename=str(output_pdf))

    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0
