import sys
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow
from app.integrations import FlightLogAndTestDataPage


class IntegratedMainWindow(MainWindow):
    def __init__(self):
        super().__init__()
        self.flight_data_page = FlightLogAndTestDataPage(self)
        self.stack.addWidget(self.flight_data_page)
        self.nav.addItem("Flight Logs & Test Data")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Drone Maintenance Assistant")
    window = IntegratedMainWindow()
    window.show()
    sys.exit(app.exec())
