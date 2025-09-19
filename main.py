import sys
from PyQt6 import QtWidgets, QtGui, QtCore
import resources_rc
from ui_python.main_window import Ui_MainWindow
from ui_python.login_window import Ui_Form as Ui_LoginWindow
from PyQt6.QtCore import pyqtSignal, QEasingCurve, QPropertyAnimation
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect

try:
    from PyQt6.QtSvg import QSvgRenderer
    SVG_AVAILABLE = True
except Exception:
    QSvgRenderer = None
    SVG_AVAILABLE = False

from custome_widgets.fancy_label import FancyLabel
from custome_widgets.round_line import RoundedLine
from custome_widgets.popup_toast import PopupToast
from custome_widgets.clickable_label import ClickableLabel
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

class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_LoginWindow()
        self.ui.setupUi(self)

        QtGui.QFontDatabase.addApplicationFont(":/fonts/RobotoMono-Regular.ttf")
        QtGui.QFontDatabase.addApplicationFont(":/fonts/SFProDisplay-Regular.ttf")

        self._make_labels_clickable()
        self._apply_header_with_fancylabel()
        self._apply_subtext_shadow()
        self._setup_button_shadow_animations()

        self.ui.loginButton.clicked.connect(self.on_login_clicked)
        self.ui.submitButton.clicked.connect(self.on_submit_clicked)

    def _make_labels_clickable(self):
        self.ui.registerLinkText.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.ui.registerLinkText.mousePressEvent = lambda e: self.ui.tabWidget.setCurrentIndex(1)

        self.ui.loginLinkText.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.ui.loginLinkText.mousePressEvent = lambda e: self.ui.tabWidget.setCurrentIndex(0)

        self.ui.dontHaveAccountText.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.ui.dontHaveAccountText.mousePressEvent = lambda e: self.ui.tabWidget.setCurrentIndex(1)
        self.ui.alreadyHaveAccountText.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.ui.alreadyHaveAccountText.mousePressEvent = lambda e: self.ui.tabWidget.setCurrentIndex(0)

    def _apply_header_with_fancylabel(self):
        try:
            FancyLabel(parent=self.ui.userLogin, target_label=self.ui.headerText, text=self.ui.headerText.text())
        except Exception:
            pass
        try:
            FancyLabel(parent=self.ui.userRegister, target_label=self.ui.headerTextRegister, text=self.ui.headerTextRegister.text())
        except Exception:
            pass

    def _apply_subtext_shadow(self):
        for lbl_name in ("pTextLogin", "pTextRegister"):
            lbl = getattr(self.ui, lbl_name, None)
            if lbl is None:
                continue
            try:
                lbl.setAutoFillBackground(False)
                lbl.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

                base_ss = (lbl.styleSheet() or "").strip()
                if base_ss:
                    if not base_ss.endswith(";"):
                        base_ss = base_ss + ";"
                    new_ss = base_ss + " background-color: transparent;"
                else:
                    new_ss = "background-color: transparent;"

                lbl.setStyleSheet(new_ss)

                eff = QGraphicsDropShadowEffect(lbl)
                eff.setBlurRadius(12)
                eff.setColor(QtGui.QColor(59, 130, 246, 120))
                eff.setOffset(0, 0)
                lbl.setGraphicsEffect(eff)

                lbl.update()
            except Exception:
                pass

    def _setup_button_shadow_animations(self):
        for btn in (self.ui.loginButton, self.ui.submitButton):
            try:
                eff = QGraphicsDropShadowEffect(self)
                eff.setBlurRadius(8)
                eff.setColor(QtGui.QColor(0, 0, 0, 160))
                eff.setOffset(0, 6)
                btn.setGraphicsEffect(eff)
                btn._shadow_effect = eff
                btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                btn.pressed.connect(lambda b=btn: self._btn_press_shadow(b))
                btn.released.connect(lambda b=btn: self._btn_release_shadow(b))
            except Exception:
                pass

    def _btn_press_shadow(self, btn: QtWidgets.QPushButton):
        eff = getattr(btn, "_shadow_effect", None)
        if eff is None:
            return
        anim = QPropertyAnimation(eff, b"blurRadius", self)
        anim.setDuration(110)
        anim.setStartValue(eff.blurRadius())
        anim.setEndValue(3)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        btn._shadow_press_anim = anim

        a = QtCore.QVariantAnimation(self)
        a.setDuration(110)
        a.setStartValue(eff.offset().y())
        a.setEndValue(2)
        a.valueChanged.connect(lambda v, e=eff: e.setOffset(0, float(v)))
        a.start()
        btn._shadow_offset_anim = a

    def _btn_release_shadow(self, btn: QtWidgets.QPushButton):
        eff = getattr(btn, "_shadow_effect", None)
        if eff is None:
            return
        anim = QPropertyAnimation(eff, b"blurRadius", self)
        anim.setDuration(180)
        anim.setStartValue(eff.blurRadius())
        anim.setEndValue(8)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)
        anim.start()
        btn._shadow_release_anim = anim

        a = QtCore.QVariantAnimation(self)
        a.setDuration(180)
        a.setStartValue(eff.offset().y())
        a.setEndValue(6)
        a.valueChanged.connect(lambda v, e=eff: e.setOffset(0, float(v)))
        a.start()
        btn._shadow_offset_release_anim = a

    def validate_login(self) -> tuple[bool, str]:
        email = self.ui.emailLineEdit.text().strip()
        pwd = self.ui.passwordLineEdit.text()
        if not email:
            return False, "Email is required"
        if "@gmail.com" not in email.lower():
            return False, "Email must be a Gmail address"
        if len(pwd) < 8:
            return False, "Password must be at least 8 characters"
        return True, ""

    def validate_submit(self) -> tuple[bool, str]:
        username = self.ui.usernameLineEditRegister.text().strip()
        email = self.ui.emailLineEditRegister.text().strip()
        pwd = self.ui.passwordLineEditRegister.text()
        confirm = self.ui.confirmPasswordLineEditRegister.text()
        if not username:
            return False, "Username is required"
        if not email:
            return False, "Email is required"
        if "@gmail.com" not in email.lower():
            return False, "Email must be a Gmail address"
        if len(pwd) < 8:
            return False, "Password must be at least 8 characters"
        if pwd != confirm:
            return False, "Password and confirm do not match"
        return True, ""

    def on_login_clicked(self):
        ok, msg = self.validate_login()
        if not ok:
            self._show_toast(msg)
            return

        email = self.ui.emailLineEdit.text().strip()
        password = self.ui.passwordLineEdit.text()
        print("Login OK ->", {"email": email, "password": password})
        self._show_toast("Login OK — values printed to console", duration=1800)

    def on_submit_clicked(self):
        ok, msg = self.validate_submit()
        if not ok:
            self._show_toast(msg)
            return

        username = self.ui.usernameLineEditRegister.text().strip()
        email = self.ui.emailLineEditRegister.text().strip()
        password = self.ui.passwordLineEditRegister.text()
        print("Submit OK ->", {"username": username, "email": email, "password": password})
        self._show_toast("Account created (sample)", duration=1800)

    def _show_toast(self, text: str, duration: int = 2500):
        toast = PopupToast(self, text=text, duration=duration)
        toast.show_toast()


if __name__ == "__main__":
    
    manage_db = ManageDatabase()
    manage_db.init_db()
    backaddr_full = manage_db.get_backaddr()
    backaddr_full = f"{backaddr_full['sub']}.{backaddr_full['name']}.{backaddr_full['tld']}:{backaddr_full['port']}"

    app = QtWidgets.QApplication(sys.argv)
    main_window = MainAppWindow()
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec())
