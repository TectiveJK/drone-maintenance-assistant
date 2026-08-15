from PySide6.QtWidgets import *
from PySide6.QtGui import QFont
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
  self.pages=[self.dashboard(),self.fleet(),self.inspection("Pre-Flight Inspection",PRE_FLIGHT),self.inspection("Post-Flight Inspection",POST_FLIGHT),self.placeholder("Batteries"),self.placeholder("Maintenance Tasks"),self.placeholder("Faults / Incidents"),self.placeholder("Reports")]
  for p in self.pages:self.stack.addWidget(p)
  self.nav.currentRowChanged.connect(self.change_page); self.nav.setCurrentRow(0)
 def build_style(self):
  self.setStyleSheet("QMainWindow,QWidget#root,QStackedWidget{background:#b8bcc1;} QLabel{color:#000000;} QListWidget{background:#252b31;color:#ffffff;border:0;padding:12px;} QListWidget::item{color:#ffffff;padding:15px 10px;border-radius:6px;margin:2px;} QListWidget::item:selected{background:#46515b;color:#ffffff;} QLabel#title{font-size:29px;font-weight:700;color:#000000;} QLabel#subtitle{color:#000000;} QGroupBox{background:#d9dcdf;border:1px solid #aeb4b9;border-radius:9px;padding:10px;color:#000000;} QGroupBox::title{color:#000000;} QPushButton{background:#e5e7e9;border:1px solid #92999f;padding:9px 16px;border-radius:6px;color:#000000;} QPushButton:hover{background:#f0f1f2;color:#000000;} QDialogButtonBox QPushButton{color:#000000;} QTableWidget{background:#e1e3e5;border:1px solid #9da4aa;gridline-color:#c3c7ca;color:#000000;} QTableWidget::item{color:#000000;} QHeaderView::section{background:#cbd0d4;padding:8px;font-weight:600;color:#000000;} QLineEdit,QTextEdit,QComboBox{background:#eef0f1;border:1px solid #9da4aa;padding:6px;color:#000000;} QLineEdit:disabled,QTextEdit:disabled,QComboBox:disabled{color:#000000;} QComboBox QAbstractItemView{background:#eef0f1;color:#000000;selection-background-color:#cbd0d4;selection-color:#000000;} QAbstractSpinBox{color:#000000;}")
 def title(self,text,sub):
  w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,8); a=QLabel(text); a.setObjectName("title"); l.addWidget(a); s=QLabel(sub); s.setObjectName("subtitle"); l.addWidget(s); return w
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
 def placeholder(self,name):
  p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title(name,f"{name} workspace")); l.addWidget(QLabel("Module interface will be expanded in the next build.")); l.addStretch(); return p
 def change_page(self,index): self.stack.setCurrentIndex(index); self.refresh()
 def refresh(self):
  c=connect(); drones=c.execute("SELECT * FROM drones ORDER BY name").fetchall(); inspections=c.execute("SELECT COUNT(*) n FROM inspections").fetchone()["n"]; issues=c.execute("SELECT COUNT(*) n FROM maintenance_issues WHERE status='OPEN'").fetchone()["n"]; c.close()
  while self.stats.count(): item=self.stats.takeAt(0); w=item.widget(); w.deleteLater() if w else None
  for name,val in [("Drones",len(drones)),("Inspections",inspections),("Open Issues",issues)]:
   box=QGroupBox(name); box.setMinimumHeight(100); q=QVBoxLayout(box); n=QLabel(str(val)); n.setFont(QFont("Sans",24,QFont.Bold)); q.addWidget(n); self.stats.addWidget(box)
  self.summary.setText("All drone technical information is entered by the operator when required.")
  self.fleet_table.setRowCount(len(drones))
  for r,x in enumerate(drones):
   for col,key in enumerate(["name","manufacturer","model","serial_number","firmware","equipment","flight_hours","flight_count"]): self.fleet_table.setItem(r,col,QTableWidgetItem(str(x[key] or "")))
  for page in self.pages[2:4]:
   page.combo.clear()
   for x in drones: page.combo.addItem(f"{x['name']} — {x['model'] or 'Model not set'}",x['id'])
