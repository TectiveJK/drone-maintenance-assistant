import json
import os
import shutil
import subprocess
import urllib.request
from datetime import datetime
from ftplib import FTP
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget
)

from app.database import connect, now
from app.reports import export_pdf_report

LOG_EXTENSIONS = {".ulg", ".bin", ".log", ".tlog", ".csv", ".px4log", ".dat", ".jsonl", ".json", ".txt"}
LOG_PREVIEW_BYTES = 1024 * 1024


def _black(widget):
    widget.setStyleSheet("color:#000;background:#eef0f1;")


def _pick_folder_with_files(parent, start_dir):
    start = str(Path(start_dir))
    filename = start if start.endswith(os.sep) else start + os.sep
    zenity = shutil.which("zenity")
    if zenity:
        try:
            result = subprocess.run(
                [
                    zenity,
                    "--file-selection",
                    "--directory",
                    "--title=Select local log folder",
                    f"--filename={filename}",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                chosen = result.stdout.strip()
                if chosen:
                    return chosen
            return ""
        except OSError:
            pass
    return QFileDialog.getExistingDirectory(
        parent,
        "Select local log folder",
        start,
        QFileDialog.Option.ShowDirsOnly,
    )


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


def _log_preview_text(path, limit=LOG_PREVIEW_BYTES):
    path = Path(path)
    size = path.stat().st_size
    data = path.read_bytes()[:limit]
    try:
        body = data.decode("utf-8")
    except UnicodeDecodeError:
        body = data.decode("utf-8", errors="replace").replace("\x00", "")
    body = _format_log_body(path, body)
    header = f"File: {path.name}\nPath: {path}\nSize: {size:,} bytes\n\n"
    if size > limit:
        body += f"\n\n--- Preview truncated after {limit:,} of {size:,} bytes ---"
    return header + (body if str(body).strip() else "(This log file has no displayable text.)")


def _format_log_body(path, body):
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        chunks = []
        for line in body.splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                chunks.append(json.dumps(json.loads(raw), indent=2, ensure_ascii=False))
            except Exception:
                chunks.append(raw)
        return "\n\n".join(chunks) if chunks else body
    if suffix == ".json":
        try:
            return json.dumps(json.loads(body), indent=2, ensure_ascii=False)
        except Exception:
            return body
    return body


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
        self.drone = self.main_window.drone_combo(persist=True)
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
        self.logs.currentItemChanged.connect(self.preview_selected_log)
        self.logs.itemClicked.connect(self.preview_selected_log)
        root.addWidget(QLabel("Log file contents:"))
        self.log_preview = QTextEdit()
        self.log_preview.setReadOnly(True)
        self.log_preview.setPlaceholderText("Select a log file above to view its contents.")
        self.log_preview.setFont(QFont("Monospace", 10))
        _black(self.log_preview)
        root.addWidget(self.log_preview, 2)
        log_buttons = QHBoxLayout()
        refresh = QPushButton("Refresh Log List")
        refresh.clicked.connect(self.refresh_logs)
        export_btn = QPushButton("Export PDF")
        export_btn.clicked.connect(self.export_log_list_pdf)
        log_buttons.addWidget(refresh)
        log_buttons.addWidget(export_btn)
        log_buttons.addStretch()
        root.addLayout(log_buttons)
        return page

    def report_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        row = QHBoxLayout()
        open_btn = QPushButton("Open Drone Flight Test Reporter JSON")
        open_btn.clicked.connect(self.import_report)
        refresh = QPushButton("Refresh Imported Reports")
        refresh.clicked.connect(self.refresh_reports)
        export_btn = QPushButton("Export PDF")
        export_btn.clicked.connect(self.export_imported_report_pdf)
        row.addWidget(open_btn)
        row.addWidget(refresh)
        row.addWidget(export_btn)
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
        start = Path(self.local_folder.text()).expanduser()
        if start.is_dir():
            start_dir = start
        elif start.parent.is_dir():
            start_dir = start.parent
        else:
            start_dir = Path.home()
        path = _pick_folder_with_files(self, start_dir)
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
        selected = None
        if hasattr(self, "logs") and self.logs.currentItem() is not None:
            selected = self.logs.currentItem().data(Qt.UserRole)
        self.logs.clear()
        if hasattr(self, "log_preview"):
            self.log_preview.clear()
        folder = Path(self.local_folder.text()).expanduser()
        restore = -1
        for index, path in enumerate(_log_files(folder)):
            item = QListWidgetItem(
                f"{path.name} — {path.stat().st_size:,} bytes — {datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')}"
            )
            item.setData(Qt.UserRole, str(path))
            self.logs.addItem(item)
            if selected and str(path) == selected:
                restore = index
        if restore >= 0:
            self.logs.setCurrentRow(restore)
        elif self.logs.count() > 0 and selected is None:
            self.logs.setCurrentRow(0)

    def preview_selected_log(self, current, _previous=None):
        if not hasattr(self, "log_preview"):
            return
        if current is None:
            self.log_preview.clear()
            return
        path = current.data(Qt.UserRole)
        if not path:
            self.log_preview.setPlainText("No file path is stored for this log.")
            return
        try:
            self.log_preview.setPlainText(_log_preview_text(path))
            self.log_preview.moveCursor(QTextCursor.MoveOperation.Start)
        except Exception as exc:
            self.log_preview.setPlainText(f"Could not read this log file.\n{exc}")

    def export_log_list_pdf(self):
        self.refresh_logs()
        drone = self.drone.currentText() if hasattr(self, "drone") else "Select drone"
        folder = self.local_folder.text() if hasattr(self, "local_folder") else ""
        items = [self.logs.item(i).text() for i in range(self.logs.count())] if hasattr(self, "logs") else []
        lines = [
            "FLIGHT LOG LIST",
            f"Generated: {now()}",
            f"Assigned drone: {drone}",
            f"Local log folder: {folder}",
            f"Status: {self.status.text() if hasattr(self, 'status') else ''}",
            "",
            "Retrieved / discovered flight logs:",
        ]
        lines.extend(items or ["No flight logs found."])
        lines.extend(["", "Log file contents:", ""])
        selected = self.logs.currentItem() if hasattr(self, "logs") else None
        file_path = selected.data(Qt.UserRole) if selected is not None else None
        if file_path:
            try:
                lines.append(_log_preview_text(file_path))
            except Exception as exc:
                lines.append(f"Could not read the selected log file.\n{exc}")
        elif hasattr(self, "log_preview") and self.log_preview.toPlainText().strip():
            lines.append(self.log_preview.toPlainText())
        else:
            folder_path = Path(folder).expanduser()
            logs = _log_files(folder_path)
            if not logs:
                lines.append("No log content to include.")
            else:
                for log_path in logs:
                    lines.append("-" * 48)
                    try:
                        lines.append(_log_preview_text(log_path))
                    except Exception as exc:
                        lines.append(f"Could not read {log_path.name}.\n{exc}")
                    lines.append("")
        suggested = str(Path.home() / f"flight_log_list_{now().replace(':','-')}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", suggested, "PDF files (*.pdf)")
        if not path:
            return
        try:
            saved = export_pdf_report("\n".join(lines), path)
            QMessageBox.information(self, "Export PDF", f"Report saved to:\n{saved}")
        except Exception as error:
            QMessageBox.warning(self, "Export PDF", f"Could not save the PDF.\n{error}")

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

    def export_imported_report_pdf(self):
        text = self.report_preview.toPlainText().strip() if hasattr(self, "report_preview") else ""
        if not text:
            QMessageBox.warning(self, "Export PDF", "Select a report to export first.")
            return
        suggested = str(Path.home() / f"flight_test_report_{now().replace(':','-')}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", suggested, "PDF files (*.pdf)")
        if not path:
            return
        try:
            saved = export_pdf_report(text, path)
            QMessageBox.information(self, "Export PDF", f"Report saved to:\n{saved}")
        except Exception as error:
            QMessageBox.warning(self, "Export PDF", f"Could not save the PDF.\n{error}")
