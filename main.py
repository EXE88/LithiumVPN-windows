# main.py
import sys
from PyQt6 import QtWidgets, QtGui, QtCore
import resources_rc
from ui_python.main_window import Ui_MainWindow

try:
    from PyQt6.QtSvg import QSvgRenderer
    SVG_AVAILABLE = True
except Exception:
    QSvgRenderer = None
    SVG_AVAILABLE = False

from custome_widgets.fancy_label import FancyLabel
from custome_widgets.round_line import RoundedLine
from custome_widgets.fancy_round_button import FancyRoundButton
from modules.database import ManageDatabase

class MainAppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        QtGui.QFontDatabase.addApplicationFont(":/fonts/RobotoMono-Regular.ttf")
        QtGui.QFontDatabase.addApplicationFont(":/fonts/SFProDisplay-Regular.ttf")

        self._initial_setup()
        self._connect_signals()

        self.manage_db = ManageDatabase()
        self.manage_db.init_db()

    def _initial_setup(self):
        username = "danial1388"
        self.ui.usernameText.setFixedWidth(len(username) * 10)
        self.ui.usernameText.setText(username)
        self.ui.coinNumber.setText("160")
        self.ui.selectConfigComboBox.clear()
        self.ui.selectConfigComboBox.addItems([
            "Iran-06lw1wpj", "Iran-d7r9arzn", "Iran-ye0NdN6j", "Iran-7nmSP6LR"
        ])

        try:
            self.ui.continueProfileLine.hide()
        except Exception:
            pass

        self.rounded_line = RoundedLine(parent=self.ui.homeTab,
                                        x=25.5, y=65,
                                        length=71.7, thickness=2.3,
                                        color=QtGui.QColor(230, 230, 230),
                                        vertical=True)

        self.header = FancyLabel(self.ui.homeTab, self.ui.headerText, "LithiumVPN")

        try:
            if hasattr(self.ui, "powerButtonBase") and self.ui.powerButtonBase is not None:
                self.ui.powerButtonBase.hide()
                self.ui.powerButtonBase.setParent(None)
                self.ui.powerButtonBase.deleteLater()
                try:
                    delattr(self.ui, "powerButtonBase")
                except Exception:
                    pass
        except Exception:
            pass

        try:
            children = self.ui.centralwidget.findChildren(QtWidgets.QWidget)
            for ch in children:
                try:
                    if ch.objectName() == "powerButtonBase":
                        ch.hide()
                        ch.setParent(None)
                        ch.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass

        btn_geom = None
        try:
            if hasattr(self.ui, "powerButton") and self.ui.powerButton is not None:
                btn_geom = self.ui.powerButton.geometry()
                self.ui.powerButton.hide()
                self.ui.powerButton.setParent(None)
                self.ui.powerButton.deleteLater()
        except Exception:
            btn_geom = None

        if btn_geom is None:
            btn_geom = QtCore.QRect(100, 140, 200, 200)

        parent = self.ui.homeTab
        svg_path = ':/icons/icons/power.svg'

        diameter = btn_geom.width()
        self.power_button_fancy = FancyRoundButton(
            parent=parent,
            diameter=diameter,
            svg_path=svg_path,
            halo_color=QtGui.QColor(255, 255, 255),
            halo_alpha=220,
            ring_color=QtGui.QColor(0, 0, 0, 0),
            ring_width=0,
            halo_scale=0.75,
            halo_blur_factor=0.35,
            halo_inner_ratio=0.45
        )
        self.power_button_fancy.setGeometry(btn_geom)
        self.ui.powerButton = self.power_button_fancy

        self.power_button_fancy.set_state("disconnected")

        self.ui.menuButton.raise_()
        self.ui.sideMenu.raise_()

    def _connect_signals(self):
        try:
            self.ui.powerButton.clicked.connect(self.on_power_clicked)
        except Exception:
            pass
        self.ui.menuButton.clicked.connect(self.on_menu_clicked)
        self.ui.sideMenuHomeButton.clicked.connect(lambda: self.on_sidebutton_clicked("Home"))
        self.ui.sideMenuAccountButton.clicked.connect(lambda: self.on_sidebutton_clicked("Account"))

    def on_power_clicked(self):
        current = self.ui.connectionStatusText.text()
        if current in ("Not Connected", "Disconnected"):
            self.power_button_fancy.set_state("connecting")
            self.ui.connectionStatusText.setText("Connecting...")
            self.ui.selectConfigComboBox.setDisabled(True)
            QtCore.QTimer.singleShot(2000, self._on_connected)
        else:
            self.power_button_fancy.set_state("disconnected")
            self.ui.connectionStatusText.setText("Disconnected")
            self.ui.selectConfigComboBox.setDisabled(False)

    def _on_connected(self):
        self.power_button_fancy.set_state("connected")
        self.ui.connectionStatusText.setText("Connected")
        self.ui.selectConfigComboBox.setDisabled(True)


    def on_menu_clicked(self):
        QtWidgets.QMessageBox.information(self, "Menu", "Menu clicked")

    def on_sidebutton_clicked(self, name):
        QtWidgets.QMessageBox.information(self, name, f"{name} clicked")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainAppWindow()
    window.show()
    sys.exit(app.exec())
