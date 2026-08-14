from PySide6.QtWidgets import *
from PySide6.QtGui import QFont
from app.database import init_db, connect, now

PRE_FLIGHT = ["Airframe condition", "Propellers", "Motors", "Landing gear", "Battery", "Battery contacts", "Payload / camera", "GNSS / GPS", "Sensors", "LEDs", "Remote controller", "Cables / connectors", "Communications", "Firmware", "Physical damage"]
POST_FLIGHT = ["Airframe damage", "Propellers after flight", "Motors / abnormal noise", "Battery condition", "Battery temperature", "Payload / camera condition", "Landing gear", "Sensors", "Cables / connectors", "General cleanliness"]

class DroneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Drone")
        self.resize(520, 500)
        f = QFormLayout(self)
        self.name, self.man, self.model, self.serial, self.fw = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.hardware, self.notes = QTextEdit(), QTextEdit()
        for label, widget in [("Drone name *", self.name), ("Manufacturer", self.man), ("Model", self.model), ("Serial number", self.serial), ("Firmware", self.fw), ("Equipment / Hardware", self.hardware), ("Notes", self.notes)]: f.addRow(label, widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate); buttons.rejected.connect(self.reject); f.addRow(buttons)
    def validate(self):
        if not self.name.text().strip(): QMessageBox.warning(self, "Missing information", "Drone name is required."); return
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); init_db(); self.setWindowTitle("Drone Maintenance Assistant"); self.resize(1300, 800); self.build_style()
        root = QWidget(); root.setObjectName("root"); layout = QHBoxLayout(root)
        self.nav = QListWidget(); self.nav.setFixedWidth(235); self.nav.addItems(["Dashboard", "Drone Fleet", "Pre-Flight Inspection", "Post-Flight Inspection", "Batteries", "Maintenance Tasks", "Faults / Incidents", "Reports"])
        self.stack = QStackedWidget(); layout.addWidget(self.nav); layout.addWidget(self.stack); self.setCentralWidget(root)
        self.pages = [self.dashboard(), self.fleet(), self.inspection("Pre-Flight Inspection", PRE_FLIGHT), self.inspection("Post-Flight Inspection", POST_FLIGHT), self.placeholder("Batteries"), self.placeholder("Maintenance Tasks"), self.placeholder("Faults / Incidents"), self.placeholder("Reports")]
        for page in self.pages: self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.change_page); self.nav.setCurrentRow(0)
    def build_style(self):
        self.setStyleSheet("QMainWindow,QWidget#root,QStackedWidget{background:#b8bcc1;} QListWidget{background:#252b31;color:white;border:0;padding:12px;} QListWidget::item{padding:15px 10px;border-radius:6px;margin:2px;} QListWidget::item:selected{background:#46515b;} QLabel#title{font-size:29px;font-weight:700;color:#20252a;} QLabel#subtitle{color:#4f5961;} QGroupBox{background:#d9dcdf;border:1px solid #aeb4b9;border-radius:9px;padding:10px;} QPushButton{background:#e5e7e9;border:1px solid #92999f;padding:9px 16px;border-radius:6px;} QPushButton:hover{background:#f0f1f2;} QTableWidget{background:#e1e3e5;border:1px solid #9da4aa;gridline-color:#c3c7ca;} QHeaderView::section{background:#cbd0d4;padding:8px;font-weight:600;} QLineEdit,QTextEdit,QComboBox{background:#eef0f1;border:1px solid #9da4aa;padding:6px;}")
    def title(self, text, sub):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0,0,0,8); a = QLabel(text); a.setObjectName("title"); l.addWidget(a); s = QLabel(sub); s.setObjectName("subtitle"); l.addWidget(s); return w
    def dashboard(self):
        p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title("Dashboard","First-level drone maintenance and field inspection")); self.stats=QHBoxLayout(); l.addLayout(self.stats); self.summary=QLabel(); l.addWidget(self.summary); l.addStretch(); return p
    def fleet(self):
        p=QWidget(); l=QVBoxLayout(p); row=QHBoxLayout(); row.addWidget(self.title("Drone Fleet","Register aircraft and enter technical information when required")); row.addStretch(); add=QPushButton("+ Add Drone"); add.clicked.connect(self.add_drone); row.addWidget(add); l.addLayout(row)
        self.fleet_table=QTableWidget(0,8); self.fleet_table.setHorizontalHeaderLabels(["Name","Manufacturer","Model","Serial","Firmware","Equipment / Hardware","Flight hours","Flights"]); self.fleet_table.horizontalHeader().setStretchLastSection(True); l.addWidget(self.fleet_table); return p
    def add_drone(self):
        dialog=DroneDialog(self)
        if dialog.exec() == QDialog.Accepted:
            c=connect(); c.execute("INSERT INTO drones(name,manufacturer,model,serial_number,firmware,equipment,notes,created_at) VALUES(?,?,?,?,?,?,?,?)", (dialog.name.text().strip(),dialog.man.text().strip(),dialog.model.text().strip(),dialog.serial.text().strip(),dialog.fw.text().strip(),dialog.hardware.toPlainText().strip(),dialog.notes.toPlainText().strip(),now())); c.commit(); c.close(); self.refresh(); QMessageBox.information(self,"Drone added","The drone has been added to the fleet.")
    def inspection(self, kind, items):
        p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title(kind,"Guided inspection — record PASS, FAIL or N/A")); row=QHBoxLayout(); row.addWidget(QLabel("Aircraft:")); combo=QComboBox(); row.addWidget(combo,1); l.addLayout(row)
        table=QTableWidget(len(items),3); table.setHorizontalHeaderLabels(["Inspection item","Result","Notes"]); table.setColumnWidth(0,300); table.horizontalHeader().setStretchLastSection(True)
        for r,item in enumerate(items):
            table.setItem(r,0,QTableWidgetItem(item)); result=QComboBox(); result.addItems(["PASS","FAIL","N/A"]); table.setCellWidget(r,1,result); table.setItem(r,2,QTableWidgetItem(""))
        l.addWidget(table); notes=QTextEdit(); notes.setPlaceholderText("Overall inspection notes..."); l.addWidget(notes); complete=QPushButton("Complete Inspection"); complete.clicked.connect(lambda:self.save_inspection(combo,table,items,kind,notes)); l.addWidget(complete); p.combo=combo; return p
    def save_inspection(self, combo, table, items, kind, notes):
        if combo.currentData() is None: QMessageBox.warning(self,"No drone","Add a drone before starting an inspection."); return
        c=connect(); cur=c.execute("INSERT INTO inspections(drone_id,inspection_type,status,notes,created_at) VALUES(?,?,?,?,?)",(combo.currentData(),kind,"PASS",notes.toPlainText(),now())); iid=cur.lastrowid; failed=[]
        for r,item in enumerate(items):
            result=table.cellWidget(r,1).currentText(); note=table.item(r,2).text(); c.execute("INSERT INTO inspection_items(inspection_id,item_name,result,notes) VALUES(?,?,?,?)",(iid,item,result,note));
            if result=="FAIL": failed.append(item)
        if failed:
            c.execute("UPDATE inspections SET status='FAIL' WHERE id=?",(iid,))
            for item in failed: c.execute("INSERT INTO maintenance_issues(drone_id,source,description,status,created_at) VALUES(?,?,?,?,?)",(combo.currentData(),kind,item,"OPEN",now()))
        c.commit(); c.close(); QMessageBox.information(self,"Inspection saved",f"{kind} completed. Result: {'FAIL' if failed else 'PASS'}"); self.refresh()
    def placeholder(self, name):
        p=QWidget(); l=QVBoxLayout(p); l.addWidget(self.title(name,f"{name} workspace")); l.addWidget(QLabel("Module interface will be expanded in the next build.")); l.addStretch(); return p
    def change_page(self,index): self.stack.setCurrentIndex(index); self.refresh()
    def refresh(self):
        c=connect(); drones=c.execute("SELECT * FROM drones ORDER BY name").fetchall(); inspections=c.execute("SELECT COUNT(*) n FROM inspections").fetchone()["n"]; issues=c.execute("SELECT COUNT(*) n FROM maintenance_issues WHERE status='OPEN'").fetchone()["n"]; c.close()
        while self.stats.count(): item=self.stats.takeAt(0); widget=item.widget(); widget.deleteLater() if widget else None
        for name,value in [("Drones",len(drones)),("Inspections",inspections),("Open Issues",issues)]:
            box=QGroupBox(name); box.setMinimumHeight(100); q=QVBoxLayout(box); value_label=QLabel(str(value)); value_label.setFont(QFont("Sans",24,QFont.Bold)); q.addWidget(value_label); self.stats.addWidget(box)
        self.summary.setText("All drone technical information is entered by the operator when required.")
        self.fleet_table.setRowCount(len(drones))
        for r,drone in enumerate(drones):
            for col,key in enumerate(["name","manufacturer","model","serial_number","firmware","equipment","flight_hours","flight_count"]): self.fleet_table.setItem(r,col,QTableWidgetItem(str(drone[key] or "")))
        for page in self.pages[2:4]:
            page.combo.clear()
            for drone in drones: page.combo.addItem(f"{drone['name']} — {drone['model'] or 'Model not set'}",drone['id'])
