from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox, QComboBox, QMessageBox
from app.database import init_db, connect, now

INSPECTION_ITEMS = ["Airframe condition", "Propellers", "Motors", "Landing gear", "Battery", "Battery contacts", "Payload / camera", "GNSS / GPS", "Sensors", "LEDs", "Remote controller", "Cables / connectors", "Communications", "Firmware", "Physical damage"]

class DroneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Drone")
        form = QFormLayout(self)
        self.name = QLineEdit(); self.manufacturer = QLineEdit(); self.model = QLineEdit(); self.serial = QLineEdit(); self.firmware = QLineEdit(); self.hardware = QTextEdit(); self.notes = QTextEdit()
        form.addRow("Drone name *", self.name); form.addRow("Manufacturer", self.manufacturer); form.addRow("Model", self.model); form.addRow("Serial number", self.serial); form.addRow("Firmware", self.firmware); form.addRow("Equipment / Hardware", self.hardware); form.addRow("Notes", self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); form.addRow(buttons)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); init_db(); self.setWindowTitle("Drone Maintenance Assistant"); self.resize(1200, 760)
        self.setStyleSheet("QMainWindow{background:#f4f6f8} QListWidget{background:#17212b;color:white;border:0;padding:10px} QListWidget::item{padding:14px} QListWidget::item:selected{background:#2d4052} QLabel#title{font-size:28px;font-weight:bold} QPushButton{padding:8px 14px} QTableWidget{background:white}")
        root=QWidget(); layout=QHBoxLayout(root); self.nav=QListWidget(); self.nav.addItems(["Dashboard","Drone Fleet","Pre-Flight Inspection","Maintenance Issues"]); self.nav.setFixedWidth(220); self.stack=QStackedWidget(); layout.addWidget(self.nav); layout.addWidget(self.stack); self.setCentralWidget(root)
        self.dashboard_page=self.dashboard(); self.fleet_page=self.fleet(); self.inspection_page=self.inspection(); self.issues_page=self.issues()
        for p in [self.dashboard_page,self.fleet_page,self.inspection_page,self.issues_page]: self.stack.addWidget(p)
        self.nav.currentRowChanged.connect(self.switch_page); self.nav.setCurrentRow(0)

    def header(self, text):
        label=QLabel(text); label.setObjectName("title"); return label

    def dashboard(self):
        page=QWidget(); l=QVBoxLayout(page); l.addWidget(self.header("Dashboard")); self.stats=QLabel(); self.issue_summary=QLabel(); l.addWidget(self.stats); l.addWidget(self.issue_summary); l.addStretch(); return page

    def fleet(self):
        page=QWidget(); l=QVBoxLayout(page); row=QHBoxLayout(); row.addWidget(self.header("Drone Fleet")); row.addStretch(); add=QPushButton("+ Add Drone"); add.clicked.connect(self.add_drone); row.addWidget(add); l.addLayout(row)
        self.fleet_table=QTableWidget(0,7); self.fleet_table.setHorizontalHeaderLabels(["Name","Manufacturer","Model","Serial","Firmware","Equipment / Hardware","Notes"]); self.fleet_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.fleet_table); return page

    def add_drone(self):
        dlg=DroneDialog(self)
        if dlg.exec() and dlg.name.text().strip():
            con=connect(); con.execute("INSERT INTO drones(name,manufacturer,model,serial_number,firmware,equipment,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",(dlg.name.text().strip(),dlg.manufacturer.text(),dlg.model.text(),dlg.serial.text(),dlg.firmware.text(),dlg.hardware.toPlainText(),dlg.notes.toPlainText(),now())); con.commit(); con.close(); self.refresh()

    def inspection(self):
        page=QWidget(); l=QVBoxLayout(page); l.addWidget(self.header("Pre-Flight Inspection")); top=QHBoxLayout(); top.addWidget(QLabel("Drone:")); self.drone_combo=QComboBox(); top.addWidget(self.drone_combo,1); l.addLayout(top)
        self.inspect_table=QTableWidget(len(INSPECTION_ITEMS),3); self.inspect_table.setHorizontalHeaderLabels(["Inspection item","Result","Notes"]); self.inspect_table.horizontalHeader().setStretchLastSection(True)
        for r,item in enumerate(INSPECTION_ITEMS):
            self.inspect_table.setItem(r,0,QTableWidgetItem(item)); c=QComboBox(); c.addItems(["PASS","FAIL","N/A"]); self.inspect_table.setCellWidget(r,1,c); self.inspect_table.setItem(r,2,QTableWidgetItem(""))
        l.addWidget(self.inspect_table); save=QPushButton("Complete Inspection"); save.clicked.connect(self.save_inspection); l.addWidget(save); return page

    def save_inspection(self):
        if self.drone_combo.currentData() is None: QMessageBox.warning(self,"No drone","Add a drone first."); return
        con=connect(); cur=con.execute("INSERT INTO inspections(drone_id,inspection_type,status,notes,created_at) VALUES(?,?,?,?,?)",(self.drone_combo.currentData(),"Pre-Flight","PASS","",now())); iid=cur.lastrowid; failed=[]
        for r,item in enumerate(INSPECTION_ITEMS):
            result=self.inspect_table.cellWidget(r,1).currentText(); note=self.inspect_table.item(r,2).text(); con.execute("INSERT INTO inspection_items(inspection_id,item_name,result,notes) VALUES(?,?,?,?)",(iid,item,result,note))
            if result=="FAIL": failed.append(item)
        if failed:
            con.execute("UPDATE inspections SET status='FAIL' WHERE id=?",(iid,))
            for item in failed: con.execute("INSERT INTO maintenance_issues(drone_id,source,description,status,created_at) VALUES(?,?,?,?,?)",(self.drone_combo.currentData(),"Pre-Flight Inspection",item,"OPEN",now()))
        con.commit(); con.close(); QMessageBox.information(self,"Inspection complete","Inspection saved. " + (f"{len(failed)} maintenance issue(s) opened." if failed else "Result: PASS.")); self.refresh()

    def issues(self):
        page=QWidget(); l=QVBoxLayout(page); l.addWidget(self.header("Maintenance Issues")); self.issue_table=QTableWidget(0,5); self.issue_table.setHorizontalHeaderLabels(["Drone","Source","Issue","Status","Created"]); self.issue_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.issue_table); return page

    def switch_page(self,index): self.stack.setCurrentIndex(index); self.refresh()

    def refresh(self):
        con=connect(); drones=con.execute("SELECT * FROM drones ORDER BY name").fetchall(); issues=con.execute("SELECT d.name,m.source,m.description,m.status,m.created_at FROM maintenance_issues m JOIN drones d ON d.id=m.drone_id ORDER BY m.created_at DESC").fetchall(); inspections=con.execute("SELECT COUNT(*) c FROM inspections").fetchone()["c"]; con.close()
        self.stats.setText(f"Drones: {len(drones)}    |    Inspections: {inspections}    |    Open maintenance issues: {sum(1 for x in issues if x['status']=='OPEN')}")
        self.issue_summary.setText("First-level maintenance workspace — all drone information can be entered by the operator when needed.")
        self.fleet_table.setRowCount(len(drones))
        for r,row in enumerate(drones):
            for c,key in enumerate(["name","manufacturer","model","serial_number","firmware","equipment","notes"]): self.fleet_table.setItem(r,c,QTableWidgetItem(str(row[key] or "")))
        self.drone_combo.clear(); [self.drone_combo.addItem(f"{x['name']} — {x['model'] or 'Model not set'}",x['id']) for x in drones]
        self.issue_table.setRowCount(len(issues))
        for r,row in enumerate(issues):
            for c,key in enumerate(["name","source","description","status","created_at"]): self.issue_table.setItem(r,c,QTableWidgetItem(str(row[key])))
