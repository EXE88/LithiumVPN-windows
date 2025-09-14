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


class MainAppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        QtGui.QFontDatabase.addApplicationFont(":/fonts/RobotoMono-Regular.ttf")
        QtGui.QFontDatabase.addApplicationFont(":/fonts/SFProDisplay-Regular.ttf")

        self._initial_setup()
        self._connect_signals()

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

        # vertical rounded line
        self.rounded_line = RoundedLine(parent=self.ui.homeTab,
                                        x=25.5, y=65,
                                        length=71.7, thickness=2.3,
                                        color=QtGui.QColor(230, 230, 230),
                                        vertical=True)

        # header
        self.header = FancyLabel(self.ui.homeTab, self.ui.headerText, "LithiumVPN")

        # ----------------- ENSURE designer's powerButtonBase IS REMOVED -----------------
        # remove any widget named "powerButtonBase" anywhere under centralwidget
        try:
            # try attribute first
            if hasattr(self.ui, "powerButtonBase") and self.ui.powerButtonBase is not None:
                self.ui.powerButtonBase.hide()
                self.ui.powerButtonBase.setParent(None)
                self.ui.powerButtonBase.deleteLater()
                # remove attribute to be safe
                try:
                    delattr(self.ui, "powerButtonBase")
                except Exception:
                    pass
        except Exception:
            pass

        # Also scan children in case there are leftover widgets with that objectName
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
        # ------------------------------------------------------------------------------

        # remove placeholder powerButton as well (we will replace it)
        btn_geom = None
        try:
            if hasattr(self.ui, "powerButton") and self.ui.powerButton is not None:
                btn_geom = self.ui.powerButton.geometry()
                self.ui.powerButton.hide()
                self.ui.powerButton.setParent(None)
                self.ui.powerButton.deleteLater()
        except Exception:
            btn_geom = None

        # fallback geometry if nothing found
        if btn_geom is None:
            btn_geom = QtCore.QRect(100, 140, 200, 200)

        parent = self.ui.homeTab
        svg_path = ':/icons/icons/power.svg'

        # create fancy button WITHOUT external white ring (make ring transparent)
        diameter = btn_geom.width()
        self.power_button_fancy = FancyRoundButton(
            parent=parent,
            diameter=diameter,
            svg_path=svg_path,
            halo_color=QtGui.QColor(255, 255, 255),
            halo_alpha=220,
            ring_color=QtGui.QColor(0, 0, 0, 0),  # transparent ring -> no white stroke
            ring_width=0,
            halo_scale=0.75,
            halo_blur_factor=0.35,
            halo_inner_ratio=0.45
        )
        self.power_button_fancy.setGeometry(btn_geom)
        self.ui.powerButton = self.power_button_fancy

        # default state
        self.power_button_fancy.set_state("disconnected")

        # make sure menu/sidemenu above
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
            QtCore.QTimer.singleShot(2000, self._on_connected)
        else:
            self.power_button_fancy.set_state("disconnected")
            self.ui.connectionStatusText.setText("Disconnected")

    def _on_connected(self):
        self.power_button_fancy.set_state("connected")
        self.ui.connectionStatusText.setText("Connected")

    def on_menu_clicked(self):
        QtWidgets.QMessageBox.information(self, "Menu", "Menu clicked")

    def on_sidebutton_clicked(self, name):
        QtWidgets.QMessageBox.information(self, name, f"{name} clicked")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainAppWindow()
    window.show()
    sys.exit(app.exec())
