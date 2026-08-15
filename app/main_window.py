from PySide6.QtWidgets import *
from PySide6.QtGui import QFont
from PySide6.QtCore import QDate
from app.database import init_db, connect, now

PRE_FLIGHT=["Airframe condition","Propellers","Motors","Landing gear","Battery","Battery contacts","Payload / camera","GNSS / GPS","Sensors","LEDs","Remote controller","Cables / connectors","Communications","Firmware","Physical damage"]
POST_FLIGHT=["Airframe damage","Propellers after flight","Motors / abnormal noise","Battery condition","Battery temperature","Payload / camera condition","Landing gear","Sensors","Cables / connectors","General cleanliness"]

class DroneDialog(QDialog):
 def __init__(self,parent=None):
  super().__init__(parent); self.setWindowTitle("Add Drone"); self.resize(520,500); f=QFormLayout(self)
  self.name=QLineEdit(); self.man=QLineEdit(); self.model=QLineEdit(); self.serial=QLineEdit(); self.fw=QLineEdit(); self.hardware=QTextEdit(); self.notes=QTextEdit()
  for label,w in [("Drone name *",self.name),("Manufacturer",self.man),("Model",self.model),("Serial number",self.serial),("Firmware",self.fw),("Equipment / Hardware",self.hardware),("Notes",self.notes)]: f.addRow(label,w)
  b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.validate); b.rejected.connect(self.reject); f.addRow(b)
 def validate(self):
  if not self.name.text().strip(): QMessageBox.warning(self,"Missing information","Drone name is required."); return
  self.accept()

class MainWindow(QMainWindow):
 def __init__(self):
  super().__init__(); init_db(); self.setWindowTitle("Drone Maintenance Assistant"); self.resize(1300,800); self.build_style()
  root=QWidget(); root.setObjectName("root"); rl=QHBoxLayout(root); self.nav=QListWidget(); self.nav.setFixedWidth(235); self.nav.addItems(["Dashboard","Drone Fleet","Pre-Flight Inspection","Post-Flight Inspection","Batteries","Maintenance Tasks","Faults / Incidents","Reports"]); self.stack=QStackedWidget(); rl.addWidget(self.nav); rl.addWidget(self.stack); self.setCentralWidget(root)
  self.pages=[self.dashboard(),self.fleet(),self.inspection("Pre-Flight Inspection",PRE_FLIGHT),self.inspection("Post-Flight Inspection",POST_FLIGHT),self.batteries(),self.maintenance_tasks(),self.incidents(),self.reports()]
  for p in self.pages:self.stack.addWidget(p)
  self.nav.currentRowChanged.connect(self.change_page); self.nav.setCurrentRow(0); self.refresh()
 def build_style(self):
  self.setStyleSheet("QMainWindow,QWidget#root,QStackedWidget{background:#b8bcc1;} QLabel{color:#000000;} QListWidget{background:#252b31;color:#ffffff;border:0;padding:12px;} QListWidget::item{color:#ffffff;padding:15px 10px;border-radius:6px;margin:2px;} QListWidget::item:selected{background:#46515b;color:#ffffff;} QLabel#title{font-size:29px;font-weight:700;color:#000000;} QLabel#subtitle{color:#000000;} QGroupBox{background:#d9dcdf;border:1px solid #aeb4b9;border-radius:9px;padding:10px;color:#000000;} QGroupBox::title{color:#000000;} QPushButton{background:#e5e7e9;border:1px solid #92999f;padding:9px 16px;border-radius:6px;color:#000000;} QPushButton:hover{background:#f0f1f2;color:#000000;} QDialogButtonBox QPushButton{color:#000000;} QTableWidget{background:#e1e3e5;border:1px solid #9da4aa;gridline-color:#c3c7ca;color:#000000;} QTableWidget::item{color:#000000;} QHeaderView::section{background:#cbd0d4;padding:8px;font-weight:600;color:#000000;} QLineEdit,QTextEdit,QComboBox,QDateEdit{background:#eef0f1;border:1px solid #9da4aa;padding:6px;color:#000000;} QLineEdit:disabled,QTextEdit:disabled,QComboBox:disabled{color:#000000;} QComboBox QAbstractItemView{background:#eef0f1;color:#000000;selection-background-color:#cbd0d4;selection-color:#000000;} QAbstractSpinBox{color:#000000;}")
 def title(self,text,sub):
  w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,8); a=QLabel(text); a.setObjectName("title"); l.addWidget(a); s=QLabel(sub); s.setObjectName("subtitle"); l.addWidget(s); return w
 def drone_combo(self):
  combo=QComboBox(); c=connect(); drones=c.execute("SELECT id,name,model FROM drones ORDER BY name").fetchall(); c.close(); combo.addItem("Select drone...",None)
  for d in drones: combo.addItem(f"{d['name']} — {d['model'] or 'Model not set'}",d['id'])
  return combo
 def dashboard(self):
  p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title("Dashboard","First-level drone maintenance and field inspection")); self.stats=QHBoxLayout(); l.addLayout(self.stats); self.summary=QLabel(); l.addWidget(self.summary); l.addStretch(); return p
 def fleet(self):
  p=QWidget(); l=QVBoxLayout(p); r=QHBoxLayout(); r.addWidget(self.title("Drone Fleet","Register aircraft and enter technical information when required")); r.addStretch(); b=QPushButton("+ Add Drone"); b.clicked.connect(self.add_drone); r.addWidget(b); l.addLayout(r); self.fleet_table=QTableWidget(0,8); self.fleet_table.setHorizontalHeaderLabels(["Name","Manufacturer","Model","Serial","Firmware","Equipment / Hardware","Flight hours","Flights"]); self.fleet_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.fleet_table); return p
 def add_drone(self):
  d=DroneDialog(self)
  if d.exec() and d.name.text().strip():
   c=connect(); c.execute("INSERT INTO drones(name,manufacturer,model,serial_number,firmware,equipment,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",(d.name.text().strip(),d.man.text().strip(),d.model.text().strip(),d.serial.text().strip(),d.fw.text().strip(),d.hardware.toPlainText().strip(),d.notes.toPlainText().strip(),now())); c.commit(); c.close(); self.refresh(); QMessageBox.information(self,"Drone added","The drone has been added to the fleet.")
 def inspection(self,kind,items):
  p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title(kind,"Guided inspection — record PASS, FAIL or N/A")); row=QHBoxLayout(); row.addWidget(QLabel("Aircraft:")); combo=QComboBox(); row.addWidget(combo,1); l.addLayout(row); table=QTableWidget(len(items),3); table.setHorizontalHeaderLabels(["Inspection item","Result","Notes"]); table.setColumnWidth(0,300); table.horizontalHeader().setStretchLastSection(True)
  for r,it in enumerate(items): table.setItem(r,0,QTableWidgetItem(it)); q=QComboBox(); q.addItems(["PASS","FAIL","N/A"]); table.setCellWidget(r,1,q); table.setItem(r,2,QTableWidgetItem(""))
  l.addWidget(table); notes=QTextEdit(); notes.setPlaceholderText("Overall inspection notes..."); l.addWidget(notes); b=QPushButton("Complete Inspection"); b.clicked.connect(lambda:self.save_inspection(combo,table,items,kind,notes)); l.addWidget(b); p.combo=combo; return p
 def save_inspection(self,combo,table,items,kind,notes):
  if combo.currentData() is None: QMessageBox.warning(self,"No drone","Add a drone before starting an inspection."); return
  c=connect(); cur=c.execute("INSERT INTO inspections(drone_id,inspection_type,status,notes,created_at) VALUES(?,?,?,?,?)",(combo.currentData(),kind,"PASS",notes.toPlainText(),now())); iid=cur.lastrowid; fails=[]
  for r,it in enumerate(items):
   res=table.cellWidget(r,1).currentText(); note=table.item(r,2).text(); c.execute("INSERT INTO inspection_items(inspection_id,item_name,result,notes) VALUES(?,?,?,?)",(iid,it,res,note))
   if res=="FAIL": fails.append(it)
  if fails:
   c.execute("UPDATE inspections SET status='FAIL' WHERE id=?",(iid,))
   for it in fails: c.execute("INSERT INTO maintenance_issues(drone_id,source,description,status,created_at) VALUES(?,?,?,?,?)",(combo.currentData(),kind,it,"OPEN",now()))
  c.commit(); c.close(); QMessageBox.information(self,"Inspection saved",f"{kind} completed. Result: {'FAIL' if fails else 'PASS'}"); self.refresh()
 def batteries(self):
  p=QWidget(); l=QVBoxLayout(p); r=QHBoxLayout(); r.addWidget(self.title("Batteries","Track batteries, cycles, voltage and condition")); r.addStretch(); b=QPushButton("+ Add Battery"); b.clicked.connect(self.add_battery); r.addWidget(b); l.addLayout(r); self.battery_table=QTableWidget(0,7); self.battery_table.setHorizontalHeaderLabels(["Drone","Battery ID","Cycles","Voltage","Health","Notes","Added"]); self.battery_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.battery_table); return p
 def add_battery(self):
  d=QDialog(self); d.setWindowTitle("Add Battery"); d.resize(500,420); f=QFormLayout(d); drone=self.drone_combo(); bid=QLineEdit(); cycles=QSpinBox(); cycles.setRange(0,100000); voltage=QLineEdit(); voltage.setPlaceholderText("e.g. 25.2 V"); health=QComboBox(); health.addItems(["GOOD","MONITOR","REPLACE"]); notes=QTextEdit()
  for label,w in [("Drone *",drone),("Battery ID *",bid),("Cycles",cycles),("Voltage",voltage),("Health",health),("Notes",notes)]: f.addRow(label,w)
  buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); f.addRow(buttons); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject)
  if d.exec() and drone.currentData() is not None and bid.text().strip():
   c=connect(); c.execute("INSERT INTO batteries(drone_id,battery_id,cycles,voltage,health,notes,created_at) VALUES(?,?,?,?,?,?,?)",(drone.currentData(),bid.text().strip(),cycles.value(),voltage.text().strip(),health.currentText(),notes.toPlainText().strip(),now())); c.commit(); c.close(); self.refresh()
  elif d.result()==QDialog.Accepted: QMessageBox.warning(self,"Missing information","Select a drone and enter a Battery ID.")
 def maintenance_tasks(self):
  p=QWidget(); l=QVBoxLayout(p); r=QHBoxLayout(); r.addWidget(self.title("Maintenance Tasks","Create and track first-level maintenance actions")); r.addStretch(); b=QPushButton("+ Add Task"); b.clicked.connect(self.add_task); r.addWidget(b); l.addLayout(r); self.task_table=QTableWidget(0,7); self.task_table.setHorizontalHeaderLabels(["Drone","Task","Priority","Status","Due date","Notes","Created"]); self.task_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.task_table); return p
 def add_task(self):
  d=QDialog(self); d.setWindowTitle("Add Maintenance Task"); d.resize(560,480); f=QFormLayout(d); drone=self.drone_combo(); task=QLineEdit(); priority=QComboBox(); priority.addItems(["LOW","NORMAL","HIGH","CRITICAL"]); status=QComboBox(); status.addItems(["OPEN","IN PROGRESS","COMPLETED","CANCELLED"]); due=QDateEdit(QDate.currentDate()); due.setCalendarPopup(True); notes=QTextEdit()
  for label,w in [("Drone *",drone),("Task *",task),("Priority",priority),("Status",status),("Due date",due),("Notes",notes)]: f.addRow(label,w)
  buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); f.addRow(buttons); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject)
  if d.exec() and drone.currentData() is not None and task.text().strip():
   c=connect(); c.execute("INSERT INTO maintenance_tasks(drone_id,task,priority,status,due_date,notes,created_at) VALUES(?,?,?,?,?,?,?)",(drone.currentData(),task.text().strip(),priority.currentText(),status.currentText(),due.date().toString("yyyy-MM-dd"),notes.toPlainText().strip(),now())); c.commit(); c.close(); self.refresh()
  elif d.result()==QDialog.Accepted: QMessageBox.warning(self,"Missing information","Select a drone and enter a maintenance task.")
 def incidents(self):
  p=QWidget(); l=QVBoxLayout(p); r=QHBoxLayout(); r.addWidget(self.title("Faults / Incidents","Record technical faults, incidents and corrective actions")); r.addStretch(); b=QPushButton("+ Add Fault / Incident"); b.clicked.connect(self.add_incident); r.addWidget(b); l.addLayout(r); self.incident_table=QTableWidget(0,7); self.incident_table.setHorizontalHeaderLabels(["Drone","Title","Severity","Description","Action taken","Status","Created"]); self.incident_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.incident_table); return p
 def add_incident(self):
  d=QDialog(self); d.setWindowTitle("Add Fault / Incident"); d.resize(600,560); f=QFormLayout(d); drone=self.drone_combo(); title=QLineEdit(); severity=QComboBox(); severity.addItems(["LOW","MEDIUM","HIGH","CRITICAL"]); desc=QTextEdit(); action=QTextEdit(); status=QComboBox(); status.addItems(["OPEN","INVESTIGATING","RESOLVED"])
  for label,w in [("Drone *",drone),("Title *",title),("Severity",severity),("Description",desc),("Action taken",action),("Status",status)]: f.addRow(label,w)
  buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); f.addRow(buttons); buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject)
  if d.exec() and drone.currentData() is not None and title.text().strip():
   c=connect(); c.execute("INSERT INTO incidents(drone_id,title,severity,description,action_taken,created_at) VALUES(?,?,?,?,?,?)",(drone.currentData(),title.text().strip(),severity.currentText(),desc.toPlainText().strip(),action.toPlainText().strip(),now())); c.commit(); c.close(); self.refresh()
  elif d.result()==QDialog.Accepted: QMessageBox.warning(self,"Missing information","Select a drone and enter an incident title.")
 def reports(self):
  p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title("Reports","Overview of fleet condition, inspections, batteries, tasks and incidents")); buttons=QHBoxLayout(); b=QPushButton("Refresh Report"); b.clicked.connect(self.refresh); buttons.addWidget(b); b2=QPushButton("Export Report to TXT"); b2.clicked.connect(self.export_report); buttons.addWidget(b2); buttons.addStretch(); l.addLayout(buttons); self.report=QTextEdit(); self.report.setReadOnly(True); l.addWidget(self.report); return p
 def generate_report(self):
  c=connect(); drones=c.execute("SELECT * FROM drones ORDER BY name").fetchall(); ins=c.execute("SELECT COUNT(*) n FROM inspections").fetchone()["n"]; fails=c.execute("SELECT COUNT(*) n FROM inspections WHERE status='FAIL'").fetchone()["n"]; batteries=c.execute("SELECT COUNT(*) n FROM batteries").fetchone()["n"]; tasks=c.execute("SELECT COUNT(*) n FROM maintenance_tasks").fetchone()["n"]; open_tasks=c.execute("SELECT COUNT(*) n FROM maintenance_tasks WHERE status != 'COMPLETED' AND status != 'CANCELLED'").fetchone()["n"]; incidents=c.execute("SELECT COUNT(*) n FROM incidents").fetchone()["n"]; open_inc=c.execute("SELECT COUNT(*) n FROM incidents WHERE status != 'RESOLVED'").fetchone()["n"]; issues=c.execute("SELECT COUNT(*) n FROM maintenance_issues WHERE status='OPEN'").fetchone()["n"]; c.close()
  lines=["DRONE MAINTENANCE ASSISTANT REPORT",f"Generated: {now()}","","FLEET",f"Total drones: {len(drones)}","","INSPECTIONS",f"Total inspections: {ins}",f"Failed inspections: {fails}","","BATTERIES",f"Registered batteries: {batteries}","","MAINTENANCE TASKS",f"Total tasks: {tasks}",f"Open / in-progress tasks: {open_tasks}","","FAULTS / INCIDENTS",f"Total incidents: {incidents}",f"Unresolved incidents: {open_inc}",f"Open inspection issues: {issues}","","DRONE DETAILS"]
  for d in drones: lines.append(f"- {d['name']} | {d['manufacturer'] or '-'} | {d['model'] or '-'} | {d['serial_number'] or '-'} | {d['flight_hours'] or 0} h | {d['flight_count'] or 0} flights")
  return "\n".join(lines)
 def export_report(self):
  path,_=QFileDialog.getSaveFileName(self,"Save Report","drone-maintenance-report.txt","Text files (*.txt)")
  if path:
   with open(path,"w",encoding="utf-8") as f: f.write(self.generate_report())
   QMessageBox.information(self,"Report exported","The report has been saved.")
 def change_page(self,index): self.stack.setCurrentIndex(index); self.refresh()
 def refresh(self):
  c=connect(); drones=c.execute("SELECT * FROM drones ORDER BY name").fetchall(); inspections=c.execute("SELECT COUNT(*) n FROM inspections").fetchone()["n"]; issues=c.execute("SELECT COUNT(*) n FROM maintenance_issues WHERE status='OPEN'").fetchone()["n"]; batteries=c.execute("SELECT b.*,d.name drone_name FROM batteries b LEFT JOIN drones d ON d.id=b.drone_id ORDER BY b.battery_id").fetchall(); tasks=c.execute("SELECT t.*,d.name drone_name FROM maintenance_tasks t LEFT JOIN drones d ON d.id=t.drone_id ORDER BY t.due_date").fetchall(); incidents=c.execute("SELECT i.*,d.name drone_name FROM incidents i LEFT JOIN drones d ON d.id=i.drone_id ORDER BY i.created_at DESC").fetchall(); c.close()
  while self.stats.count(): item=self.stats.takeAt(0); w=item.widget(); w.deleteLater() if w else None
  for name,val in [("Drones",len(drones)),("Inspections",inspections),("Open Issues",issues)]:
   box=QGroupBox(name); box.setMinimumHeight(100); q=QVBoxLayout(box); n=QLabel(str(val)); n.setFont(QFont("Sans",24,QFont.Bold)); q.addWidget(n); self.stats.addWidget(box)
  self.summary.setText("All drone technical information is entered by the operator when required.")
  self.fleet_table.setRowCount(len(drones))
  for r,x in enumerate(drones):
   for col,key in enumerate(["name","manufacturer","model","serial_number","firmware","equipment","flight_hours","flight_count"]): self.fleet_table.setItem(r,col,QTableWidgetItem(str(x[key] or "")))
  self.battery_table.setRowCount(len(batteries))
  for r,x in enumerate(batteries):
   for col,v in enumerate([x['drone_name'] or '-',x['battery_id'],x['cycles'] or 0,x['voltage'] or '',x['health'] or '',x['notes'] or '',x['created_at']]): self.battery_table.setItem(r,col,QTableWidgetItem(str(v)))
  self.task_table.setRowCount(len(tasks))
  for r,x in enumerate(tasks):
   for col,v in enumerate([x['drone_name'] or '-',x['task'],x['priority'],x['status'],x['due_date'] or '',x['notes'] or '',x['created_at']]): self.task_table.setItem(r,col,QTableWidgetItem(str(v)))
  self.incident_table.setRowCount(len(incidents))
  for r,x in enumerate(incidents):
   for col,v in enumerate([x['drone_name'] or '-',x['title'],x['severity'],x['description'] or '',x['action_taken'] or '',x['status'],x['created_at']]): self.incident_table.setItem(r,col,QTableWidgetItem(str(v)))
  if hasattr(self,'report'): self.report.setPlainText(self.generate_report())
