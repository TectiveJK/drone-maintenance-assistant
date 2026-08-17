from PySide6.QtWidgets import *
from PySide6.QtGui import QFont
from PySide6.QtCore import QDate, Qt
from app.database import init_db, connect, now

APP_VERSION = "0.4.0"
PRE_FLIGHT=["Airframe condition","Propellers","Motors","Landing gear","Battery","Battery contacts","Payload / camera","GNSS / GPS","Sensors","LEDs","Remote controller","Cables / connectors","Communications","Firmware","Physical damage"]
POST_FLIGHT=["Airframe damage","Propellers after flight","Motors / abnormal noise","Battery condition","Battery temperature","Payload / camera condition","Landing gear","Sensors","Cables / connectors","General cleanliness"]

def black(w): w.setStyleSheet("color:#000000;background:#eef0f1;")

class DroneDialog(QDialog):
 def __init__(self,parent=None):
  super().__init__(parent); self.setWindowTitle("Add Drone"); self.resize(560,520); f=QFormLayout(self)
  self.name=QLineEdit(); self.man=QLineEdit(); self.model=QLineEdit(); self.serial=QLineEdit(); self.hardware=QTextEdit(); self.notes=QTextEdit()
  for label,w in [("Drone name *",self.name),("Manufacturer",self.man),("Model",self.model),("Serial number",self.serial),("Equipment / Hardware",self.hardware),("Notes",self.notes)]: black(w); f.addRow(label,w)
  b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.validate); b.rejected.connect(self.reject); f.addRow(b)
 def validate(self):
  if not self.name.text().strip(): QMessageBox.warning(self,"Missing information","Drone name is required."); return
  self.accept()

class MainWindow(QMainWindow):
 def __init__(self):
  super().__init__(); init_db(); self.setWindowTitle(f"Drone Maintenance Assistant v{APP_VERSION}"); self.resize(1400,850)
  central=QWidget(); self.setCentralWidget(central); layout=QHBoxLayout(central)
  self.nav=QListWidget(); self.nav.setFixedWidth(250); black(self.nav); layout.addWidget(self.nav)
  self.stack=QStackedWidget(); layout.addWidget(self.stack,1)
  self.pages=[]
  for title, builder in [("Dashboard",self.dashboard),("Drone Fleet",self.fleet),("Pre-Flight Inspection",lambda:self.inspection("Pre-Flight",PRE_FLIGHT)),("Post-Flight Inspection",lambda:self.inspection("Post-Flight",POST_FLIGHT)),("Batteries",self.batteries),("Maintenance Tasks",self.tasks),("Faults / Incidents",self.incidents),("Reports",self.reports)]:
   self.nav.addItem(title); self.pages.append(builder()); self.stack.addWidget(self.pages[-1])
  self.nav.currentRowChanged.connect(self.stack.setCurrentIndex); self.nav.setCurrentRow(0)
  self.setStyleSheet("QMainWindow,QWidget{background:#bfc3c6;color:#000;} QLabel,QLabel *{color:#000;} QLineEdit,QTextEdit,QComboBox,QSpinBox,QDateEdit,QListWidget,QTableWidget{color:#000;background:#eef0f1;} QPushButton{color:#000;background:#d6d9dc;border:1px solid #888;padding:7px;} QHeaderView::section{color:#000;background:#d0d3d6;}")
 def drone_combo(self):
  c=QComboBox(); black(c); rows=connect().execute("SELECT id,name FROM drones ORDER BY name").fetchall(); c.addItem("Select drone",None)
  for r in rows: c.addItem(r["name"],r["id"])
  return c
 def dashboard(self):
  w=QWidget(); l=QVBoxLayout(w); h=QLabel(f"Drone Maintenance Assistant v{APP_VERSION}"); h.setStyleSheet("font-size:30px;font-weight:bold;color:#000"); l.addWidget(h); l.addWidget(QLabel("Fleet maintenance, inspections, batteries, incidents and operational reports.")); return w
 def fleet(self):
  w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel("Drone Fleet")); b=QPushButton("+ Add Drone"); b.clicked.connect(self.add_drone); l.addWidget(b); self.fleet_table=QTableWidget(0,6); self.fleet_table.setHorizontalHeaderLabels(["Name","Manufacturer","Model","Serial","Equipment / Hardware","Notes"]); l.addWidget(self.fleet_table); self.refresh_fleet(); return w
 def refresh_fleet(self):
  if not hasattr(self,"fleet_table"): return
  rows=connect().execute("SELECT name,manufacturer,model,serial_number,equipment,notes FROM drones ORDER BY name").fetchall(); self.fleet_table.setRowCount(len(rows))
  for i,r in enumerate(rows):
   for j,v in enumerate(r): self.fleet_table.setItem(i,j,QTableWidgetItem(str(v or "")))
 def add_drone(self):
  d=DroneDialog(self)
  if d.exec()==QDialog.Accepted:
   c=connect(); c.execute("INSERT INTO drones(name,manufacturer,model,serial_number,equipment,notes,created_at) VALUES(?,?,?,?,?,?,?)",(d.name.text(),d.man.text(),d.model.text(),d.serial.text(),d.hardware.toPlainText(),d.notes.toPlainText(),now())); c.commit(); c.close(); self.refresh_fleet()
 def inspection(self,kind,items):
  w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel(kind+" Inspection")); t=QTableWidget(len(items),3); t.setHorizontalHeaderLabels(["Inspection item","Result","Notes"])
  for i,item in enumerate(items): t.setItem(i,0,QTableWidgetItem(item)); c=QComboBox(); c.addItems(["PASS","FAIL","N/A"]); black(c); t.setCellWidget(i,1,c); e=QLineEdit(); black(e); t.setCellWidget(i,2,e)
  l.addWidget(t); save=QPushButton("Save Inspection"); l.addWidget(save); return w
 def batteries(self): return self.simple_page("Batteries","+ Add Battery")
 def tasks(self): return self.simple_page("Maintenance Tasks","+ Add Task")
 def incidents(self): return self.simple_page("Faults / Incidents","+ Add Fault / Incident")
 def reports(self): return self.simple_page("Reports","Refresh Report")
 def simple_page(self,title,button):
  w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel(title)); b=QPushButton(button); l.addWidget(b); l.addWidget(QLabel("Operational module ready for data entry.")); return w
