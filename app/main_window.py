import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QListWidget,QStackedWidget,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QDialog,QFormLayout,QLineEdit,QTextEdit,QDialogButtonBox,QComboBox,QMessageBox,QSpinBox,QDoubleSpinBox,QDateEdit,QGroupBox,QGridLayout,QHeaderView,QAbstractItemView)
from PySide6.QtGui import QFont
from app.database import init_db, connect, now

PRE_FLIGHT=["Airframe condition","Propellers","Motors","Landing gear","Battery","Battery contacts","Payload / camera","GNSS / GPS","Sensors","LEDs","Remote controller","Cables / connectors","Communications","Firmware","Physical damage"]
POST_FLIGHT=["Airframe damage","Propellers after flight","Motors / abnormal noise","Battery condition","Battery temperature","Payload / camera condition","Landing gear","Sensors","Cables / connectors","General cleanliness"]

class DroneDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle("Add Drone"); self.resize(520,520); f=QFormLayout(self)
        self.name=QLineEdit(); self.man=QLineEdit(); self.model=QLineEdit(); self.serial=QLineEdit(); self.fw=QLineEdit(); self.hardware=QTextEdit(); self.notes=QTextEdit()
        f.addRow("Drone name *",self.name); f.addRow("Manufacturer",self.man); f.addRow("Model",self.model); f.addRow("Serial number",self.serial); f.addRow("Firmware",self.fw); f.addRow("Equipment / Hardware",self.hardware); f.addRow("Notes",self.notes)
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)

class BatteryDialog(QDialog):
    def __init__(self,drones,parent=None):
        super().__init__(parent); self.setWindowTitle("Add Battery"); f=QFormLayout(self); self.drone=QComboBox(); [self.drone.addItem(f"{d['name']} — {d['model'] or 'Model not set'}",d['id']) for d in drones]; self.bid=QLineEdit(); self.cycles=QSpinBox(); self.cycles.setRange(0,100000); self.voltage=QLineEdit(); self.health=QComboBox(); self.health.addItems(["Good","Monitor","Service required","Unknown"]); self.notes=QTextEdit()
        f.addRow("Drone",self.drone); f.addRow("Battery ID *",self.bid); f.addRow("Cycles",self.cycles); f.addRow("Voltage",self.voltage); f.addRow("Health",self.health); f.addRow("Notes",self.notes); b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)

class TaskDialog(QDialog):
    def __init__(self,drones,parent=None):
        super().__init__(parent); self.setWindowTitle("New Maintenance Task"); f=QFormLayout(self); self.drone=QComboBox(); [self.drone.addItem(d['name'],d['id']) for d in drones]; self.task=QLineEdit(); self.priority=QComboBox(); self.priority.addItems(["LOW","NORMAL","HIGH","CRITICAL"]); self.due=QLineEdit(); self.notes=QTextEdit(); f.addRow("Drone",self.drone); f.addRow("Task *",self.task); f.addRow("Priority",self.priority); f.addRow("Due date",self.due); f.addRow("Notes",self.notes); b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)

class IncidentDialog(QDialog):
    def __init__(self,drones,parent=None):
        super().__init__(parent); self.setWindowTitle("New Incident / Fault"); self.resize(520,420); f=QFormLayout(self); self.drone=QComboBox(); [self.drone.addItem(d['name'],d['id']) for d in drones]; self.title=QLineEdit(); self.severity=QComboBox(); self.severity.addItems(["LOW","MEDIUM","HIGH","CRITICAL"]); self.desc=QTextEdit(); self.action=QTextEdit(); f.addRow("Drone",self.drone); f.addRow("Title *",self.title); f.addRow("Severity",self.severity); f.addRow("Description",self.desc); f.addRow("Action taken",self.action); b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); init_db(); self.setWindowTitle("Drone Maintenance Assistant"); self.resize(1350,820); self.setMinimumSize(1100,700); self.build_style(); root=QWidget(); rl=QHBoxLayout(root); self.nav=QListWidget(); self.nav.setFixedWidth(235); self.nav.addItems(["Dashboard","Drone Fleet","Pre-Flight Inspection","Post-Flight Inspection","Batteries","Maintenance Tasks","Faults / Incidents","Reports"]); self.stack=QStackedWidget(); rl.addWidget(self.nav); rl.addWidget(self.stack); self.setCentralWidget(root)
        self.pages=[self.dashboard(),self.fleet(),self.inspection("Pre-Flight Inspection",PRE_FLIGHT),self.inspection("Post-Flight Inspection",POST_FLIGHT),self.batteries(),self.tasks(),self.incidents(),self.reports()]
        for p in self.pages:self.stack.addWidget(p)
        self.nav.currentRowChanged.connect(self.change_page); self.nav.setCurrentRow(0)
    def build_style(self):
        self.setStyleSheet("QMainWindow{background:#eef2f5} QListWidget{background:#15212b;color:#fff;border:0;padding:14px 8px} QListWidget::item{padding:14px 12px;border-radius:7px;margin:2px} QListWidget::item:selected{background:#294255} QLabel#title{font-size:30px;font-weight:700;margin-bottom:8px} QLabel#subtitle{color:#65727e;font-size:14px} QFrame#card{background:#fff;border:1px solid #dce2e7;border-radius:10px} QPushButton{padding:9px 16px;border-radius:6px} QTableWidget{background:#fff;border:1px solid #dce2e7;gridline-color:#e7ebee} QHeaderView::section{padding:8px;font-weight:600} QGroupBox{background:#fff;border:1px solid #dce2e7;border-radius:8px;margin-top:10px;padding:10px}")
    def title(self,text,sub=None):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,8); a=QLabel(text); a.setObjectName("title"); l.addWidget(a); 
        if sub: s=QLabel(sub); s.setObjectName("subtitle"); l.addWidget(s)
        return w
    def button(self,text,slot): b=QPushButton(text); b.clicked.connect(slot); return b
    def dashboard(self):
        p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title("Dashboard","First-level drone maintenance and field inspection")); self.stats=QGridLayout(); l.addLayout(self.stats); g=QGroupBox("Recent maintenance issues"); gl=QVBoxLayout(g); self.recent=QTableWidget(0,4); self.recent.setHorizontalHeaderLabels(["Drone","Issue","Status","Created"]); self.recent.horizontalHeader().setStretchLastSection(True); gl.addWidget(self.recent); l.addWidget(g); l.addStretch(); return p
    def fleet(self):
        p=QWidget(); l=QVBoxLayout(p); r=QHBoxLayout(); r.addWidget(self.title("Drone Fleet","Register aircraft and enter technical information when required")); r.addStretch(); r.addWidget(self.button("+ Add Drone",self.add_drone)); l.addLayout(r); self.fleet_table=QTableWidget(0,8); self.fleet_table.setHorizontalHeaderLabels(["Name","Manufacturer","Model","Serial","Firmware","Equipment / Hardware","Flight hours","Flights"]); self.fleet_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.fleet_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.fleet_table); return p
    def add_drone(self):
        d=DroneDialog(self)
        if d.exec() and d.name.text().strip():
            c=connect(); c.execute("INSERT INTO drones(name,manufacturer,model,serial_number,firmware,equipment,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",(d.name.text(),d.man.text(),d.model.text(),d.serial.text(),d.fw.text(),d.hardware.toPlainText(),d.notes.toPlainText(),now())); c.commit(); c.close(); self.refresh()
    def inspection(self,kind,items):
        p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title(kind,"Guided inspection — record PASS, FAIL or N/A for every item")); top=QHBoxLayout(); top.addWidget(QLabel("Aircraft")); combo=QComboBox(); top.addWidget(combo,1); l.addLayout(top); table=QTableWidget(len(items),3); table.setHorizontalHeaderLabels(["Inspection item","Result","Notes"]); table.horizontalHeader().setStretchLastSection(True); table.setColumnWidth(0,300)
        for r,it in enumerate(items): table.setItem(r,0,QTableWidgetItem(it)); q=QComboBox(); q.addItems(["PASS","FAIL","N/A"]); table.setCellWidget(r,1,q); table.setItem(r,2,QTableWidgetItem(""))
        l.addWidget(table); notes=QTextEdit(); notes.setPlaceholderText("Overall inspection notes..."); l.addWidget(notes); save=self.button("Complete Inspection",lambda:self.save_inspection(combo,table,items,kind,notes)); l.addWidget(save); p.combo=combo; p.table=table; p.notes=notes; return p
    def save_inspection(self,combo,table,items,kind,notes):
        if combo.currentData() is None: QMessageBox.warning(self,"No drone","Add a drone before starting an inspection."); return
        c=connect(); cur=c.execute("INSERT INTO inspections(drone_id,inspection_type,status,notes,created_at) VALUES(?,?,?,?,?)",(combo.currentData(),kind,"PASS",notes.toPlainText(),now())); iid=cur.lastrowid; fails=[]
        for r,it in enumerate(items):
            res=table.cellWidget(r,1).currentText(); note=table.item(r,2).text(); c.execute("INSERT INTO inspection_items(inspection_id,item_name,result,notes) VALUES(?,?,?,?)",(iid,it,res,note));
            if res=="FAIL": fails.append(it)
        if fails:
            c.execute("UPDATE inspections SET status='FAIL' WHERE id=?",(iid,)); [c.execute("INSERT INTO maintenance_issues(drone_id,source,description,status,created_at) VALUES(?,?,?,?,?)",(combo.currentData(),kind,it,"OPEN",now())) for it in fails]
        c.commit(); c.close(); QMessageBox.information(self,"Inspection saved",f"{kind} completed. Result: {'FAIL' if fails else 'PASS'}" + (f"\n{len(fails)} maintenance issue(s) opened." if fails else "")); self.refresh()
    def batteries(self):
        p=QWidget(); l=QVBoxLayout(p); r=QHBoxLayout(); r.addWidget(self.title("Batteries","Track battery identity, cycles, voltage and health")); r.addStretch(); r.addWidget(self.button("+ Add Battery",self.add_battery)); l.addLayout(r); self.battery_table=QTableWidget(0,7); self.battery_table.setHorizontalHeaderLabels(["Drone","Battery ID","Cycles","Voltage","Health","Notes","Created"]); self.battery_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.battery_table); return p
    def add_battery(self):
        c=connect(); drones=c.execute("SELECT * FROM drones ORDER BY name").fetchall(); c.close();
        if not drones: QMessageBox.warning(self,"No drones","Add a drone first."); return
        d=BatteryDialog(drones,self)
        if d.exec() and d.bid.text().strip():
            c=connect(); c.execute("INSERT INTO batteries(drone_id,battery_id,cycles,voltage,health,notes,created_at) VALUES(?,?,?,?,?,?,?)",(d.drone.currentData(),d.bid.text(),d.cycles.value(),d.voltage.text(),d.health.currentText(),d.notes.toPlainText(),now())); c.commit(); c.close(); self.refresh()
    def tasks(self):
        p=QWidget(); l=QVBoxLayout(p); r=QHBoxLayout(); r.addWidget(self.title("Maintenance Tasks","Schedule and track first-level maintenance work")); r.addStretch(); r.addWidget(self.button("+ New Task",self.add_task)); l.addLayout(r); self.task_table=QTableWidget(0,7); self.task_table.setHorizontalHeaderLabels(["Drone","Task","Priority","Status","Due","Notes","Created"]); self.task_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.task_table); return p
    def add_task(self):
        c=connect(); drones=c.execute("SELECT * FROM drones ORDER BY name").fetchall(); c.close();
        if not drones: QMessageBox.warning(self,"No drones","Add a drone first."); return
        d=TaskDialog(drones,self)
        if d.exec() and d.task.text().strip():
            c=connect(); c.execute("INSERT INTO maintenance_tasks(drone_id,task,priority,status,due_date,notes,created_at) VALUES(?,?,?,?,?,?,?)",(d.drone.currentData(),d.task.text(),d.priority.currentText(),"OPEN",d.due.text(),d.notes.toPlainText(),now())); c.commit(); c.close(); self.refresh()
    def incidents(self):
        p=QWidget(); l=QVBoxLayout(p); r=QHBoxLayout(); r.addWidget(self.title("Faults / Incidents","Record anomalies, faults and corrective actions")); r.addStretch(); r.addWidget(self.button("+ New Incident",self.add_incident)); l.addLayout(r); self.incident_table=QTableWidget(0,6); self.incident_table.setHorizontalHeaderLabels(["Drone","Title","Severity","Description","Action taken","Created"]); self.incident_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.incident_table); return p
    def add_incident(self):
        c=connect(); drones=c.execute("SELECT * FROM drones ORDER BY name").fetchall(); c.close();
        if not drones: QMessageBox.warning(self,"No drones","Add a drone first."); return
        d=IncidentDialog(drones,self)
        if d.exec() and d.title.text().strip():
            c=connect(); c.execute("INSERT INTO incidents(drone_id,title,severity,description,action_taken,created_at) VALUES(?,?,?,?,?,?)",(d.drone.currentData(),d.title.text(),d.severity.currentText(),d.desc.toPlainText(),d.action.toPlainText(),now())); c.commit(); c.close(); self.refresh()
    def reports(self):
        p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title("Reports","Export a simple maintenance snapshot for records")); l.addWidget(QLabel("Reports can be generated from the current local database. PDF reporting will be added as the next reporting layer.")); self.report_info=QLabel(); l.addWidget(self.report_info); l.addStretch(); return p
    def change_page(self,i): self.stack.setCurrentIndex(i); self.refresh()
    def refresh(self):
        c=connect(); drones=c.execute("SELECT * FROM drones ORDER BY name").fetchall(); issues=c.execute("SELECT d.name,m.description,m.status,m.created_at FROM maintenance_issues m JOIN drones d ON d.id=m.drone_id ORDER BY m.created_at DESC").fetchall(); inspections=c.execute("SELECT COUNT(*) n FROM inspections").fetchone()["n"]; batteries=c.execute("SELECT COUNT(*) n FROM batteries").fetchone()["n"]; tasks=c.execute("SELECT COUNT(*) n FROM maintenance_tasks WHERE status='OPEN'").fetchone()["n"]; incidents=c.execute("SELECT COUNT(*) n FROM incidents").fetchone()["n"]; brows=c.execute("SELECT b.*,d.name FROM batteries b LEFT JOIN drones d ON d.id=b.drone_id ORDER BY b.created_at DESC").fetchall(); trows=c.execute("SELECT t.*,d.name FROM maintenance_tasks t JOIN drones d ON d.id=t.drone_id ORDER BY t.created_at DESC").fetchall(); irows=c.execute("SELECT i.*,d.name FROM incidents i JOIN drones d ON d.id=i.drone_id ORDER BY i.created_at DESC").fetchall(); c.close()
        while self.stats.count(): w=self.stats.takeAt(0).widget(); w.deleteLater() if w else None
        vals=[("Drones",len(drones)),("Inspections",inspections),("Batteries",batteries),("Open Tasks",tasks),("Incidents",incidents),("Open Issues",sum(x['status']=='OPEN' for x in issues))]
        for idx,(name,val) in enumerate(vals): box=QGroupBox(name); q=QVBoxLayout(box); lab=QLabel(str(val)); lab.setFont(QFont("Sans",24,QFont.Bold)); q.addWidget(lab); self.stats.addWidget(box,idx//3,idx%3)
        self.recent.setRowCount(min(issues.__len__(),10))
        for r,x in enumerate(issues[:10]):
            for col,key in enumerate(["name","description","status","created_at"]): self.recent.setItem(r,col,QTableWidgetItem(str(x[key])))
        self.fleet_table.setRowCount(len(drones))
        for r,x in enumerate(drones):
            for col,key in enumerate(["name","manufacturer","model","serial_number","firmware","equipment","flight_hours","flight_count"]): self.fleet_table.setItem(r,col,QTableWidgetItem(str(x[key] or "")))
        self._fill_inspection(self.pages[2].combo,drones); self._fill_inspection(self.pages[3].combo,drones)
        self.battery_table.setRowCount(len(brows))
        for r,x in enumerate(brows):
            for col,key in enumerate(["name","battery_id","cycles","voltage","health","notes","created_at"]): self.battery_table.setItem(r,col,QTableWidgetItem(str(x[key] or "")))
        self.task_table.setRowCount(len(trows))
        for r,x in enumerate(trows):
            for col,key in enumerate(["name","task","priority","status","due_date","notes","created_at"]): self.task_table.setItem(r,col,QTableWidgetItem(str(x[key] or "")))
        self.incident_table.setRowCount(len(irows))
        for r,x in enumerate(irows):
            for col,key in enumerate(["name","title","severity","description","action_taken","created_at"]): self.incident_table.setItem(r,col,QTableWidgetItem(str(x[key] or "")))
        self.report_info.setText(f"Current records: {len(drones)} drones • {inspections} inspections • {batteries} batteries • {tasks} open tasks • {incidents} incidents")
    def _fill_inspection(self,combo,drones):
        current=combo.currentData(); combo.blockSignals(True); combo.clear(); [combo.addItem(f"{d['name']} — {d['model'] or 'Model not set'}",d['id']) for d in drones];
        if current is not None:
            idx=combo.findData(current)
            if idx>=0: combo.setCurrentIndex(idx)
        combo.blockSignals(False)

if __name__=="__main__":
    app=QApplication(sys.argv); w=MainWindow(); w.show(); sys.exit(app.exec())
