import json
import os
import urllib.request
from datetime import datetime
from ftplib import FTP
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMessageBox, QPushButton, QSpinBox, QStackedWidget,
    QTextEdit, QVBoxLayout, QWidget
)

from app.database import connect, now

LOG_EXTENSIONS = {".ulg", ".bin", ".log", ".tlog", ".csv", ".px4log", ".dat"}


def _black(widget):
    widget.setStyleSheet("color:#000;background:#eef0f1;")


def _ensure_tables():
    c = connect()
    c.execute("""CREATE TABLE IF NOT EXISTS flight_test_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT,
        project TEXT,
        test_id TEXT,
        aircraft TEXT,
        source_file TEXT,
        report_json TEXT NOT NULL,
        imported_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS retrieved_flight_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drone_id INTEGER,
        file_name TEXT NOT NULL,
        local_path TEXT NOT NULL,
        source TEXT,
        retrieved_at TEXT NOT NULL
    )""")
    c.commit()
    c.close()


def _log_files(folder):
    p = Path(folder)
    if not p.is_dir():
        return []
    return sorted(
        [x for x in p.iterdir() if x.is_file() and x.suffix.lower() in LOG_EXTENSIONS],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )


class FlightLogAndTestDataPage(QWidget):
    """Network flight-log retrieval plus interoperability with Drone Flight Test Reporter JSON."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        _ensure_tables()
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("Flight Logs & Shared Test Data")
        title.setStyleSheet("font-size:29px;font-weight:700;color:#000")
        root.addWidget(title)
        sub = QLabel(
            "Retrieve flight logs over the local LAN and use the same multi-flight JSON report format as Drone Flight Test Reporter."
        )
        sub.setStyleSheet("color:#000")
        root.addWidget(sub)

        tabs = QComboBox()
        tabs.addItems(["Flight Log Retrieval", "Shared Flight Test Reports"])
        _black(tabs)
        root.addWidget(tabs)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.log_page())
        self.stack.addWidget(self.report_page())
        root.addWidget(self.stack, 1)
        tabs.currentIndexChanged.connect(self.stack.setCurrentIndex)

    def log_page(self):
        page = QWidget()
        root = QVBoxLayout(page)

        connection = QGroupBox("Drone / Log Device Connection")
        form = QFormLayout(connection)
        self.protocol = QComboBox()
        self.protocol.addItems(["Mounted folder", "HTTP", "FTP"])
        self.host = QLineEdit()
        self.host.setPlaceholderText("Device IP address, e.g. 192.168.1.50")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(80)
        self.remote_path = QLineEdit("/")
        self.remote_path.setPlaceholderText("Remote folder or log endpoint")
        self.local_folder = QLineEdit(str(Path.home() / "DroneFlightLogs"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.choose_local_folder)
        local_row = QHBoxLayout()
        local_row.addWidget(self.local_folder)
        local_row.addWidget(browse)
        local_widget = QWidget()
        local_widget.setLayout(local_row)
        self.drone = self.main_window.drone_combo()
        self.test_connection = QPushButton("Test Connection")
        self.retrieve = QPushButton("Retrieve Latest Flight Logs")
        self.test_connection.clicked.connect(self.check_connection)
        self.retrieve.clicked.connect(self.retrieve_logs)
        self.protocol.currentTextChanged.connect(self.protocol_changed)
        for w in [self.host, self.remote_path, self.local_folder]:
            _black(w)
        _black(self.protocol)
        form.addRow("Connection type", self.protocol)
        form.addRow("Device IP / Host", self.host)
        form.addRow("Port", self.port)
        form.addRow("Remote path", self.remote_path)
        form.addRow("Local log folder", local_widget)
        form.addRow("Assign to drone", self.drone)
        buttons = QHBoxLayout()
        buttons.addWidget(self.test_connection)
        buttons.addWidget(self.retrieve)
        form.addRow(buttons)
        root.addWidget(connection)

        self.status = QLabel("Not connected")
        self.status.setStyleSheet("color:#000;font-weight:600")
        root.addWidget(self.status)
        self.logs = QListWidget()
        _black(self.logs)
        root.addWidget(QLabel("Retrieved / discovered flight logs:"))
        root.addWidget(self.logs, 1)
        refresh = QPushButton("Refresh Log List")
        refresh.clicked.connect(self.refresh_logs)
        root.addWidget(refresh)
        return page

    def report_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        row = QHBoxLayout()
        open_btn = QPushButton("Open Drone Flight Test Reporter JSON")
        open_btn.clicked.connect(self.import_report)
        refresh = QPushButton("Refresh Imported Reports")
        refresh.clicked.connect(self.refresh_reports)
        row.addWidget(open_btn)
        row.addWidget(refresh)
        row.addStretch()
        root.addLayout(row)
        self.reports = QListWidget()
        _black(self.reports)
        root.addWidget(self.reports, 1)
        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        _black(self.report_preview)
        root.addWidget(self.report_preview, 2)
        self.reports.currentRowChanged.connect(self.preview_report)
        self.refresh_reports()
        return page

    def protocol_changed(self, value):
        defaults = {"HTTP": 80, "FTP": 21, "Mounted folder": 80}
        self.port.setValue(defaults[value])
        self.host.setEnabled(value != "Mounted folder")
        self.port.setEnabled(value != "Mounted folder")
        self.remote_path.setEnabled(value != "Mounted folder")

    def choose_local_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select flight-log folder", self.local_folder.text())
        if path:
            self.local_folder.setText(path)
            self.refresh_logs()

    def check_connection(self):
        try:
            if self.protocol.currentText() == "Mounted folder":
                folder = Path(self.local_folder.text()).expanduser()
                if not folder.is_dir():
                    folder.mkdir(parents=True, exist_ok=True)
                self.status.setText(f"Ready: {folder}")
                return
            if not self.host.text().strip():
                raise RuntimeError("Enter the device IP address or hostname.")
            host = self.host.text().strip()
            if self.protocol.currentText() == "HTTP":
                url = f"http://{host}:{self.port.value()}{self.remote_path.text() or '/'}"
                with urllib.request.urlopen(url, timeout=4) as response:
                    self.status.setText(f"HTTP connection OK — {response.status}")
            else:
                ftp = FTP()
                ftp.connect(host, self.port.value(), timeout=4)
                ftp.login()
                ftp.quit()
                self.status.setText("FTP connection OK")
        except Exception as exc:
            self.status.setText(f"Connection failed: {exc}")

    def retrieve_logs(self):
        try:
            destination = Path(self.local_folder.text()).expanduser()
            destination.mkdir(parents=True, exist_ok=True)
            source = self.protocol.currentText()
            if source == "Mounted folder":
                files = _log_files(destination)
                self.status.setText(f"Found {len(files)} flight log(s) in mounted folder.")
                self.refresh_logs()
                return
            host = self.host.text().strip()
            if not host:
                raise RuntimeError("Enter the device IP address or hostname.")
            if source == "HTTP":
                self._retrieve_http(host, destination)
            else:
                self._retrieve_ftp(host, destination)
            self.refresh_logs()
        except Exception as exc:
            QMessageBox.warning(self, "Flight log retrieval failed", str(exc))

    def _retrieve_http(self, host, destination):
        # For devices exposing a single downloadable log endpoint.
        url = f"http://{host}:{self.port.value()}{self.remote_path.text() or '/'}"
        name = Path(self.remote_path.text().rstrip("/")).name or "flight-log.bin"
        if "." not in name:
            name += ".bin"
        target = destination / name
        with urllib.request.urlopen(url, timeout=20) as response, open(target, "wb") as out:
            out.write(response.read())
        self._record_log(target, url)
        self.status.setText(f"Downloaded {target.name}")

    def _retrieve_ftp(self, host, destination):
        ftp = FTP()
        ftp.connect(host, self.port.value(), timeout=5)
        ftp.login()
        ftp.cwd(self.remote_path.text() or "/")
        names = ftp.nlst()
        candidates = [n for n in names if Path(n).suffix.lower() in LOG_EXTENSIONS]
        if not candidates:
            ftp.quit()
            self.status.setText("FTP connected, but no supported flight logs were found.")
            return
        for name in candidates:
            target = destination / Path(name).name
            with open(target, "wb") as out:
                ftp.retrbinary(f"RETR {name}", out.write)
            self._record_log(target, f"ftp://{host}:{self.port.value()}{self.remote_path.text()}/{name}")
        ftp.quit()
        self.status.setText(f"Downloaded {len(candidates)} flight log(s).")

    def _record_log(self, target, source):
        c = connect()
        c.execute(
            "INSERT INTO retrieved_flight_logs(drone_id,file_name,local_path,source,retrieved_at) VALUES(?,?,?,?,?)",
            (self.drone.currentData(), target.name, str(target), source, now()),
        )
        c.commit()
        c.close()

    def refresh_logs(self):
        self.logs.clear()
        folder = Path(self.local_folder.text()).expanduser()
        for path in _log_files(folder):
            self.logs.addItem(f"{path.name} — {path.stat().st_size:,} bytes — {datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')}")

    def import_report(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Drone Flight Test Reporter JSON", str(Path.home()), "Flight Test Reports (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("flights"), list):
                raise ValueError("This JSON is not a multi-flight Drone Flight Test Reporter report.")
            c = connect()
            c.execute(
                "INSERT INTO flight_test_reports(report_id,project,test_id,aircraft,source_file,report_json,imported_at) VALUES(?,?,?,?,?,?,?)",
                (str(data.get("version", "")), data.get("project", ""), data.get("testId", ""), data.get("droneModel", ""), path, json.dumps(data), now()),
            )
            c.commit()
            c.close()
            self.refresh_reports()
            self.status.setText(f"Imported shared flight-test report: {Path(path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "Import failed", str(exc))

    def refresh_reports(self):
        if not hasattr(self, "reports"):
            return
        self.reports.clear()
        c = connect()
        rows = c.execute("SELECT id,project,test_id,aircraft,source_file,imported_at FROM flight_test_reports ORDER BY id DESC").fetchall()
        c.close()
        for r in rows:
            self.reports.addItem(f"{r['test_id'] or 'Untitled'} — {r['project'] or 'No project'} — {r['aircraft'] or 'No aircraft'} — {r['imported_at']}")
        self.report_rows = rows

    def preview_report(self, row):
        if row < 0 or row >= len(getattr(self, "report_rows", [])):
            self.report_preview.clear()
            return
        record = self.report_rows[row]
        c = connect()
        data = c.execute("SELECT report_json FROM flight_test_reports WHERE id=?", (record["id"],)).fetchone()
        c.close()
        if not data:
            return
        report = json.loads(data["report_json"])
        lines = [
            f"Test: {report.get('testId', 'Untitled')}",
            f"Project: {report.get('project', '-')}",
            f"Aircraft: {report.get('droneModel', '-')}",
            f"Overall result: {report.get('overallResult', '-')}",
            f"Flights: {len(report.get('flights', []))}",
            "",
        ]
        for flight in report.get("flights", []):
            lines.extend([
                f"Flight {flight.get('flightNumber', '?')}: {flight.get('flightResult', 'Pending')}",
                f"  Mission: {flight.get('missionId', '-')}",
                f"  Battery: {flight.get('batteryId', '-')}",
                f"  Log: {flight.get('flightLogPath', '-')}",
                f"  Anomalies: {flight.get('anomalies', '-')}",
                "",
            ])
        self.report_preview.setPlainText("\n".join(lines))
