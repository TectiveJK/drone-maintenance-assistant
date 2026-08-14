from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget, QLabel, QPushButton
from app.database import init_db

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self.setWindowTitle("Drone Maintenance Assistant")
        self.resize(1100, 700)
        root = QWidget()
        layout = QHBoxLayout(root)
        self.nav = QListWidget()
        self.nav.addItems(["Dashboard", "Drone Fleet", "Pre-Flight Inspection", "Maintenance Issues"])
        self.nav.setFixedWidth(220)
        self.stack = QStackedWidget()
        pages = [self.dashboard(), self.placeholder("Drone Fleet"), self.placeholder("Pre-Flight Inspection"), self.placeholder("Maintenance Issues")]
        for page in pages:
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack)
        self.setCentralWidget(root)
        self.nav.setCurrentRow(0)

    def dashboard(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Drone Maintenance Assistant")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("First-level maintenance and inspection system"))
        layout.addStretch()
        return page

    def placeholder(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(title)
        label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(label)
        layout.addWidget(QLabel("Module under construction"))
        layout.addStretch()
        return page
