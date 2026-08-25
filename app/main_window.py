from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtCore import QDate
from PySide6.QtGui import QFont
from app.database import init_db, connect, now
from app.reports import export_pdf_report

APP_VERSION = "0.4.0"
PRE_FLIGHT=["Airframe condition","Propellers","Motors","Landing gear","Battery","Battery contacts","Payload / camera","GNSS / GPS","Sensors","LEDs","Remote controller","Cables / connectors","Communications","Firmware","Physical damage"]
POST_FLIGHT=["Airframe damage","Propellers after flight","Motors / abnormal noise","Battery condition","Battery temperature","Payload / camera condition","Landing gear","Sensors","Cables / connectors","General cleanliness"]

def black(w):
    w.setStyleSheet("color:#000000;background:#eef0f1;")

def notes_edit(min_height=140):
    w=QTextEdit(); black(w); w.setAcceptRichText(False); w.setMinimumHeight(min_height); w.setPlaceholderText("Write notes..."); return w

class DroneDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle("Add Drone"); self.resize(640,680); f=QFormLayout(self)
        self.name=QLineEdit(); self.man=QLineEdit(); self.model=QLineEdit(); self.serial=QLineEdit(); self.hardware=QTextEdit(); self.hardware.setMinimumHeight(90); self.notes=notes_edit(160)
        for label,w in [("Drone name *",self.name),("Manufacturer",self.man),("Model",self.model),("Serial number",self.serial),("Equipment / Hardware",self.hardware),("Notes",self.notes)]: black(w); f.addRow(label,w)
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.validate); b.rejected.connect(self.reject); f.addRow(b)
    def validate(self):
        if not self.name.text().strip(): QMessageBox.warning(self,"Missing information","Drone name is required."); return
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); init_db(); self.setWindowTitle(f"Drone Maintenance Assistant v{APP_VERSION}"); self.resize(1400,850)
        central=QWidget(); self.setCentralWidget(central); layout=QHBoxLayout(central)
        self.nav=QListWidget(); self.nav.setFixedWidth(250)
        nav_font=self.nav.font(); nav_font.setBold(True); self.nav.setFont(nav_font)
        self.nav.setStyleSheet("color:#000000;background:#eef0f1;font-weight:700;")
        layout.addWidget(self.nav)
        self.stack=QStackedWidget(); layout.addWidget(self.stack,1); self.pages=[]
        for title,builder in [("Dashboard",self.dashboard),("Drone Fleet",self.fleet),("Pre-Flight Inspection",lambda:self.inspection("Pre-Flight",PRE_FLIGHT)),("Post-Flight Inspection",lambda:self.inspection("Post-Flight",POST_FLIGHT)),("Batteries",self.batteries),("Maintenance Tasks",self.tasks),("Faults / Incidents",self.incidents),("Reports",self.reports)]:
            self.nav.addItem(title); self.pages.append(builder()); self.stack.addWidget(self.pages[-1])
        self.nav.currentRowChanged.connect(self.change_page); self.nav.setCurrentRow(0)
        self.setStyleSheet("QMainWindow,QWidget{background:#bfc3c6;color:#000;} QLabel,QLabel *{color:#000;} QLineEdit,QTextEdit,QComboBox,QSpinBox,QDateEdit,QListWidget,QTableWidget{color:#000;background:#eef0f1;} QComboBox QAbstractItemView{color:#000;background:#eef0f1;selection-background-color:#46515b;selection-color:#fff;} QPushButton{color:#000;background:#d6d9dc;border:1px solid #888;padding:7px;} QHeaderView::section{color:#000;background:#d0d3d6;}")
    def change_page(self,index):
        self.stack.setCurrentIndex(index)
        self.refresh_drone_combos()
    def fill_drone_combo(self,combo):
        required=getattr(combo,"_required",True)
        selected=combo.currentData() if combo.count() else None
        combo.blockSignals(True)
        combo.clear()
        con=connect(); rows=con.execute("SELECT id,name FROM drones ORDER BY name").fetchall(); con.close()
        combo.addItem("Select drone" if required else "No drone assigned",None)
        for r in rows: combo.addItem(r["name"],r["id"])
        if selected is not None:
            idx=combo.findData(selected)
            if idx>=0: combo.setCurrentIndex(idx)
        combo.blockSignals(False)
    def drone_combo(self,required=True,persist=False):
        c=QComboBox(); black(c); c._required=required; self.fill_drone_combo(c)
        if persist:
            self._drone_combos=getattr(self,"_drone_combos",[]); self._drone_combos.append(c)
        return c
    def refresh_drone_combos(self):
        alive=[]
        for combo in getattr(self,"_drone_combos",[]):
            try:
                combo.count(); self.fill_drone_combo(combo); alive.append(combo)
            except RuntimeError:
                continue
        self._drone_combos=alive
    def dashboard(self):
        w=QWidget(); l=QVBoxLayout(w); h=QLabel(f"Drone Maintenance Assistant v{APP_VERSION}"); h.setStyleSheet("font-size:30px;font-weight:bold;color:#000"); l.addWidget(h); l.addWidget(QLabel("Fleet maintenance, inspections, batteries, incidents and operational reports.")); return w
    def fleet(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel("Drone Fleet")); b=QPushButton("+ Add Drone"); b.clicked.connect(self.add_drone); l.addWidget(b); self.fleet_table=QTableWidget(0,6); self.fleet_table.setHorizontalHeaderLabels(["Name","Manufacturer","Model","Serial","Equipment / Hardware","Notes"]); self.fleet_table.setWordWrap(True); self.fleet_table.verticalHeader().setDefaultSectionSize(48); self.fleet_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.fleet_table); self.refresh_fleet(); return w
    def refresh_fleet(self):
        if not hasattr(self,"fleet_table"): return
        rows=connect().execute("SELECT name,manufacturer,model,serial_number,equipment,notes FROM drones ORDER BY name").fetchall(); self.fleet_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate(r): self.fleet_table.setItem(i,j,QTableWidgetItem(str(v or "")))
    def add_drone(self):
        d=DroneDialog(self)
        if d.exec()==QDialog.Accepted:
            c=connect(); c.execute("INSERT INTO drones(name,manufacturer,model,serial_number,equipment,notes,created_at) VALUES(?,?,?,?,?,?,?)",(d.name.text(),d.man.text(),d.model.text(),d.serial.text(),d.hardware.toPlainText(),d.notes.toPlainText(),now())); c.commit(); c.close(); self.refresh_fleet(); self.refresh_data_pages()
    def inspection(self,kind,items):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel(kind+" Inspection")); drone=self.drone_combo(persist=True); w.drone_combo=drone; l.addWidget(drone); t=QTableWidget(len(items),3); t.setHorizontalHeaderLabels(["Inspection item","Result","Notes"]); t.setColumnWidth(0,280); t.setColumnWidth(1,110); t.horizontalHeader().setStretchLastSection(True); t.verticalHeader().setDefaultSectionSize(78)
        for i,item in enumerate(items): t.setItem(i,0,QTableWidgetItem(item)); c=QComboBox(); c.addItems(["PASS","FAIL","N/A"]); black(c); t.setCellWidget(i,1,c); e=notes_edit(64); t.setCellWidget(i,2,e)
        l.addWidget(t); save=QPushButton("Save Inspection"); save.clicked.connect(lambda:self.save_inspection(kind,drone,t)); l.addWidget(save); return w
    def save_inspection(self,kind,drone,t):
        if drone.currentData() is None: QMessageBox.warning(self,"Select drone","Please select a drone first."); return
        results=[]; overall="PASS"
        for i in range(t.rowCount()):
            result=t.cellWidget(i,1).currentText(); note_w=t.cellWidget(i,2); note=note_w.toPlainText() if hasattr(note_w,"toPlainText") else note_w.text(); results.append((t.item(i,0).text(),result,note)); overall="FAIL" if result=="FAIL" else overall
        c=connect(); cur=c.execute("INSERT INTO inspections(drone_id,inspection_type,status,notes,created_at) VALUES(?,?,?,?,?)",(drone.currentData(),kind,overall,"",now())); iid=cur.lastrowid
        c.executemany("INSERT INTO inspection_items(inspection_id,item_name,result,notes) VALUES(?,?,?,?)",[(iid,a,b,d) for a,b,d in results]); c.commit(); c.close(); QMessageBox.information(self,"Saved",f"{kind} inspection saved as {overall}.")
    def batteries(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel("Batteries")); b=QPushButton("+ Add Battery"); b.clicked.connect(self.add_battery); l.addWidget(b); self.battery_table=QTableWidget(0,7); self.battery_table.setHorizontalHeaderLabels(["Battery ID","Drone","Cycles","Voltage","Health","Notes","Created"]); self.battery_table.setWordWrap(True); self.battery_table.verticalHeader().setDefaultSectionSize(48); self.battery_table.horizontalHeader().setSectionResizeMode(5,QHeaderView.Stretch); l.addWidget(self.battery_table); self.refresh_batteries(); return w
    def refresh_batteries(self):
        if not hasattr(self,"battery_table"): return
        rows=connect().execute("SELECT b.battery_id,COALESCE(d.name,''),b.cycles,b.voltage,b.health,b.notes,b.created_at FROM batteries b LEFT JOIN drones d ON d.id=b.drone_id ORDER BY b.id DESC").fetchall(); self.battery_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate(r): self.battery_table.setItem(i,j,QTableWidgetItem(str(v or "")))
    def add_battery(self):
        d=QDialog(self); d.setWindowTitle("Add Battery"); d.resize(560,560); f=QFormLayout(d); bid=QLineEdit(); drone=self.drone_combo(False); cycles=QSpinBox(); cycles.setRange(0,100000); voltage=QLineEdit(); health=QComboBox(); health.addItems(["Good","Monitor","Replace"]); notes=notes_edit(140)
        for x in [bid,drone,cycles,voltage,health,notes]: black(x)
        f.addRow("Battery ID *",bid); f.addRow("Drone",drone); f.addRow("Cycles",cycles); f.addRow("Voltage",voltage); f.addRow("Health",health); f.addRow("Notes",notes); buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); f.addRow(buttons)
        if d.exec()==QDialog.Accepted:
            if not bid.text().strip(): QMessageBox.warning(self,"Missing information","Battery ID is required."); return
            c=connect(); c.execute("INSERT INTO batteries(drone_id,battery_id,cycles,voltage,health,notes,created_at) VALUES(?,?,?,?,?,?,?)",(drone.currentData(),bid.text().strip(),cycles.value(),voltage.text().strip(),health.currentText(),notes.toPlainText(),now())); c.commit(); c.close(); self.refresh_batteries()
    def tasks(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel("Maintenance Tasks")); row=QHBoxLayout(); add=QPushButton("+ Add Task"); add.clicked.connect(self.add_task); delete=QPushButton("Delete Task"); delete.clicked.connect(self.delete_task); row.addWidget(add); row.addWidget(delete); row.addStretch(); l.addLayout(row); self.task_table=QTableWidget(0,7); self.task_table.setHorizontalHeaderLabels(["Drone","Task","Priority","Status","Due Date","Notes","Created"]); self.task_table.setWordWrap(True); self.task_table.verticalHeader().setDefaultSectionSize(48); self.task_table.horizontalHeader().setSectionResizeMode(5,QHeaderView.Stretch); self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.task_table.setSelectionMode(QAbstractItemView.SingleSelection); self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.task_table); self.refresh_tasks(); return w
    def refresh_tasks(self):
        if not hasattr(self,"task_table"): return
        rows=connect().execute("SELECT t.id,COALESCE(d.name,''),t.task,t.priority,t.status,t.due_date,t.notes,t.created_at FROM maintenance_tasks t JOIN drones d ON d.id=t.drone_id ORDER BY t.id DESC").fetchall(); self.task_ids=[r["id"] for r in rows]; self.task_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate(r[1:]): self.task_table.setItem(i,j,QTableWidgetItem(str(v or "")))
    def add_task(self):
        d=QDialog(self); d.setWindowTitle("Add Maintenance Task"); d.resize(560,580); f=QFormLayout(d); drone=self.drone_combo(); task=QLineEdit(); priority=QComboBox(); priority.addItems(["LOW","NORMAL","HIGH","CRITICAL"]); status=QComboBox(); status.addItems(["OPEN","IN PROGRESS","COMPLETED"]); due=QDateEdit(QDate.currentDate()); due.setCalendarPopup(True); notes=notes_edit(140)
        for x in [drone,task,priority,status,due,notes]: black(x)
        f.addRow("Drone *",drone); f.addRow("Task *",task); f.addRow("Priority",priority); f.addRow("Status",status); f.addRow("Due date",due); f.addRow("Notes",notes); buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); f.addRow(buttons)
        if d.exec()==QDialog.Accepted:
            if drone.currentData() is None or not task.text().strip(): QMessageBox.warning(self,"Missing information","Drone and task are required."); return
            c=connect(); c.execute("INSERT INTO maintenance_tasks(drone_id,task,priority,status,due_date,notes,created_at) VALUES(?,?,?,?,?,?,?)",(drone.currentData(),task.text().strip(),priority.currentText(),status.currentText(),due.date().toString("yyyy-MM-dd"),notes.toPlainText(),now())); c.commit(); c.close(); self.refresh_tasks()
    def delete_task(self):
        row=self.task_table.currentRow() if hasattr(self,"task_table") else -1
        ids=getattr(self,"task_ids",[])
        if row<0 or row>=len(ids):
            QMessageBox.warning(self,"Delete Task","Select a task to delete."); return
        name=self.task_table.item(row,1).text() if self.task_table.item(row,1) else "this task"
        if QMessageBox.question(self,"Delete Task",f"Delete the selected task?\n{name}")!=QMessageBox.StandardButton.Yes: return
        c=connect(); c.execute("DELETE FROM maintenance_tasks WHERE id=?",(ids[row],)); c.commit(); c.close(); self.refresh_tasks(); self.refresh_report()
    def incidents(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel("Faults / Incidents")); b=QPushButton("+ Add Fault / Incident"); b.clicked.connect(self.add_incident); l.addWidget(b); self.incident_table=QTableWidget(0,7); self.incident_table.setHorizontalHeaderLabels(["Drone","Title","Severity","Description","Action Taken","Status","Created"]); l.addWidget(self.incident_table); self.refresh_incidents(); return w
    def refresh_incidents(self):
        if not hasattr(self,"incident_table"): return
        rows=connect().execute("SELECT COALESCE(d.name,''),i.title,i.severity,i.description,i.action_taken,i.status,i.created_at FROM incidents i JOIN drones d ON d.id=i.drone_id ORDER BY i.id DESC").fetchall(); self.incident_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate(r): self.incident_table.setItem(i,j,QTableWidgetItem(str(v or "")))
    def add_incident(self):
        d=QDialog(self); d.setWindowTitle("Add Fault / Incident"); d.resize(620,640); f=QFormLayout(d); drone=self.drone_combo(); title=QLineEdit(); severity=QComboBox(); severity.addItems(["LOW","MEDIUM","HIGH","CRITICAL"]); desc=notes_edit(140); desc.setPlaceholderText("Describe the fault or incident..."); action=notes_edit(120); action.setPlaceholderText("Action taken..."); status=QComboBox(); status.addItems(["OPEN","INVESTIGATING","RESOLVED"])
        for x in [drone,title,severity,desc,action,status]: black(x)
        f.addRow("Drone *",drone); f.addRow("Title *",title); f.addRow("Severity",severity); f.addRow("Description",desc); f.addRow("Action Taken",action); f.addRow("Status",status); buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); f.addRow(buttons)
        if d.exec()==QDialog.Accepted:
            if drone.currentData() is None or not title.text().strip(): QMessageBox.warning(self,"Missing information","Drone and title are required."); return
            c=connect(); c.execute("INSERT INTO incidents(drone_id,title,severity,description,action_taken,status,created_at) VALUES(?,?,?,?,?,?,?)",(drone.currentData(),title.text().strip(),severity.currentText(),desc.toPlainText(),action.toPlainText(),status.currentText(),now())); c.commit(); c.close(); self.refresh_incidents()
    def reports(self):
        w=QWidget(); l=QVBoxLayout(w)
        heading=QLabel("Reports"); heading.setStyleSheet("font-size:22px;font-weight:700;color:#000"); l.addWidget(heading)
        row=QHBoxLayout()
        refresh=QPushButton("Refresh Report"); refresh.setMinimumHeight(40); refresh.clicked.connect(self.refresh_report)
        export_btn=QPushButton("Export PDF"); export_btn.setMinimumHeight(40); export_btn.setMinimumWidth(180); export_btn.clicked.connect(self.export_report_pdf)
        row.addWidget(refresh,1); row.addWidget(export_btn,1)
        l.addLayout(row)
        self.report_text=QTextEdit(); self.report_text.setReadOnly(True); black(self.report_text); l.addWidget(self.report_text)
        self.refresh_report(); return w
    def refresh_report(self):
        c=connect(); drones=c.execute("SELECT COUNT(*) n FROM drones").fetchone()["n"]; batteries=c.execute("SELECT COUNT(*) n FROM batteries").fetchone()["n"]; tasks=c.execute("SELECT COUNT(*) n FROM maintenance_tasks").fetchone()["n"]; open_tasks=c.execute("SELECT COUNT(*) n FROM maintenance_tasks WHERE status!='COMPLETED'").fetchone()["n"]; incidents=c.execute("SELECT COUNT(*) n FROM incidents").fetchone()["n"]; open_incidents=c.execute("SELECT COUNT(*) n FROM incidents WHERE status!='RESOLVED'").fetchone()["n"]; inspections=c.execute("SELECT COUNT(*) n FROM inspections").fetchone()["n"]; failed=c.execute("SELECT COUNT(*) n FROM inspections WHERE status='FAIL'").fetchone()["n"]; c.close()
        self.report_text.setPlainText(f"DRONE MAINTENANCE REPORT\nVersion: {APP_VERSION}\nGenerated: {now()}\n\nFleet\n- Drones: {drones}\n- Batteries: {batteries}\n\nMaintenance\n- Tasks: {tasks}\n- Open / active tasks: {open_tasks}\n\nFaults / Incidents\n- Total incidents: {incidents}\n- Open / investigating incidents: {open_incidents}\n\nInspections\n- Total inspections: {inspections}\n- Failed inspections: {failed}")
    def export_report_pdf(self):
        if not hasattr(self,"report_text"): return
        self.refresh_report()
        suggested=str(Path.home()/f"drone_maintenance_report_{now().replace(':','-')}.pdf")
        path,_=QFileDialog.getSaveFileName(self,"Export PDF",suggested,"PDF files (*.pdf)")
        if not path: return
        try:
            saved=export_pdf_report(self.report_text.toPlainText(),path)
            QMessageBox.information(self,"Export PDF",f"Report saved to:\n{saved}")
        except Exception as error:
            QMessageBox.warning(self,"Export PDF",f"Could not save the PDF.\n{error}")
    def refresh_data_pages(self):
        self.refresh_batteries(); self.refresh_tasks(); self.refresh_incidents(); self.refresh_report(); self.refresh_drone_combos()
