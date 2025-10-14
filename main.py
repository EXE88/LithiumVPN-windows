import sys
import threading
import sqlite3
import webbrowser
from PyQt6 import QtWidgets, QtGui, QtCore
import resources_rc
from ui_python.main_window import Ui_MainWindow
from ui_python.login_window import Ui_Form as Ui_LoginWindow
from ui_python.verify_email_window import Ui_Form as Ui_VerifyEmailWindow
from PyQt6.QtCore import pyqtSignal, QEasingCurve, QPropertyAnimation, Qt, QSize, QRect
from PyQt6.QtGui import QColor

try:
    from PyQt6.QtSvg import QSvgRenderer
    SVG_AVAILABLE = True
except Exception:
    QSvgRenderer = None
    SVG_AVAILABLE = False

from custome_widgets.fancy_label import FancyLabel, FancyLabelBetter
from custome_widgets.round_line import RoundedLine
from custome_widgets.popup_toast import PopupToast
from custome_widgets.clickable_label import ClickableLabel
from custome_widgets.fancy_round_button import FancyRoundButton
from custome_widgets.config_delegate_comboBox import ConfigDelegateComboBox
from modules.database import ManageDatabase
from modules.api_calls import ApiCalls

from core.handlers.manager import XrayClient

from configuration import CONFIG

class MainAppWindow(QtWidgets.QMainWindow):

    logout_finished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        QtGui.QFontDatabase.addApplicationFont(":/fonts/RobotoMono-Regular.ttf")
        QtGui.QFontDatabase.addApplicationFont(":/fonts/SFProDisplay-Regular.ttf")

        self.logout_finished.connect(self._on_logout_finished)

        self.product_name = CONFIG['PRODUCT_NAME']
        self.admin_telegram = CONFIG['ADMIN_TELEGRAM_ID']
        self.coin_price = CONFIG['COIN_PRICE']

        self.toman_unit_x = self.ui.buyCoinsTomanUnitText.x()

        self._initial_setup()
        self._connect_signals()

    def _initial_setup(self):
        self.setWindowTitle(self.product_name)

        self.user_details_status, self.user_details = api_calls.get_user()
        if self.user_details_status and isinstance(self.user_details, dict):
            self.coin_count = str(self.user_details.get("coin_count", 0))
            username = self.user_details.get("username", "")
            email = self.user_details.get("email", "")
            self.ui.usernameText.setFixedWidth(len(username) * 10)
            self.ui.usernameText.setText(username)
            self.ui.accountUsernameText.setText(username)
            self.ui.accountEmailText.setText(email)
            self.ui.coinNumber.setText(str(self.user_details.get("coin_count", 0)))
            self.ui.accountCoinsCount.setText(str(self.user_details.get("coin_count", 0)))
            self.ui.selectConfigComboBox.clear()
            self.ui.selectConfigComboBox.setView(QtWidgets.QListView(self.ui.selectConfigComboBox))
            self.ui.selectConfigComboBox.view().setVerticalScrollBarPolicy(
                QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self.ui.selectConfigComboBox.setMaxVisibleItems(2) 

            configs = self.user_details.get("config_codes", []) or []
            for cfg in configs:
                code_full = cfg.get("config_code", "")
                display_name = code_full.split("#")[1] if "#" in code_full else code_full
                gb = cfg.get("gb_left") or 0
                days = cfg.get("days_left") or 0

                config_codes[display_name] = code_full

                try:
                    days_val = float(days)
                except Exception:
                    days_val = days
                if isinstance(days_val, (int, float)) and days_val <= 0:
                    days = "expired"
                self.ui.selectConfigComboBox.addItem(display_name)
                i = self.ui.selectConfigComboBox.count() - 1
                self.ui.selectConfigComboBox.setItemData(i, {"gb": gb, "days": days}, Qt.ItemDataRole.UserRole)

            all_configs_count = len(configs)
            expired_configs_count = 0
            for cfg in configs:
                days = cfg.get("days_left") or 0
                try:
                    days_val = float(days)
                except Exception:
                    days_val = None
                if isinstance(days_val, (int, float)) and days_val <= 0:
                    expired_configs_count += 1
            self.ui.accountAllConfigsCount.setText(str(all_configs_count))
            self.ui.accountExpiredConfigsCount.setText(str(expired_configs_count))

            self.ui.selectConfigComboBox.setItemDelegate(ConfigDelegateComboBox(self.ui.selectConfigComboBox))
            self.ui.selectConfigComboBox.setEditable(False)
        else:
            self.coin_count = 0
            self._show_toast(self.user_details, 3000)

        try:
            self.ui.continueProfileLine.hide()
        except Exception:
            pass

        self.rounded_line = RoundedLine(parent=self.ui.homeTab,
                                        x=25.5, y=65,
                                        length=71.7, thickness=2.3,
                                        color=QtGui.QColor(230, 230, 230),
                                        vertical=True)

        self.header = FancyLabel(self.ui.homeTab, self.ui.headerText, self.product_name)
        self.account_header = FancyLabel(self.ui.accountTab, self.ui.accountHeaderText, self.product_name)
        self.buycoin_header = FancyLabel(self.ui.buyCoinsTab, self.ui.buyCoinsHeaderText, self.product_name)

        self.ui.buyCoinsAdminID.setText(CONFIG['ADMIN_TELEGRAM_ID'])
        self.buycoin_adminid = FancyLabelBetter(self.ui.buyCoinsTab, self.ui.buyCoinsAdminID, self.ui.buyCoinsAdminID.text(),
                                                    glow_color=(255, 255, 255, 220), shadow_color=(255, 255, 255, 120), 
                                                    header_color_stop0=(255, 255, 255, 255), header_color_stop1=(230, 230, 230, 255))
        
        self.buycoin_description = FancyLabelBetter(self.ui.buyCoinsTab, self.ui.buyCoinsDescription, self.ui.buyCoinsDescription.text(),
                                                    glow_color=(255, 215, 0, 200), shadow_color=(184, 134, 11, 160), 
                                                    header_color_stop0=(212, 175, 55, 255), header_color_stop1=(255, 223, 132, 255))

        self.ui.buyCoinsCoinPriceText.setText(f"Price of Each Coin : {CONFIG['COIN_PRICE']} Tomans")
        self.buycoin_price_text = FancyLabelBetter(self.ui.buyCoinsTab, self.ui.buyCoinsCoinPriceText, self.ui.buyCoinsCoinPriceText.text(),
                                                    glow_color=(255, 255, 255, 220), shadow_color=(255, 255, 255, 120), 
                                                    header_color_stop0=(255, 255, 255, 255), header_color_stop1=(230, 230, 230, 255))

        self.ui.buyCoinsYourCoinsText.setText(f"You Have : {self.coin_count} Coins")
        self.buycoin_your_coins = FancyLabelBetter(self.ui.buyCoinsTab, self.ui.buyCoinsYourCoinsText, self.ui.buyCoinsYourCoinsText.text(),
                                                    glow_color=(255, 255, 255, 220), shadow_color=(255, 255, 255, 120), 
                                                    header_color_stop0=(255, 255, 255, 255), header_color_stop1=(230, 230, 230, 255))

        self.ui.buyCoinsEqualMoneyNumber.setText(str(CONFIG['COIN_PRICE']))

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

        self.menu_toggle = False

    def refresh_user_data(self):
        try:
            status, data = api_calls.get_user()
        except Exception as e:
            status, data = False, f"Error fetching user: {e}"

        if status and isinstance(data, dict):
            self.user_details_status = status
            self.user_details = data
            username = self.user_details.get("username", "")
            email = self.user_details.get("email", "")
            try:
                self.ui.usernameText.setFixedWidth(max(1, len(username)) * 10)
                self.ui.usernameText.setText(username)
                self.ui.accountUsernameText.setText(username)
                self.ui.accountEmailText.setText(email)
            except Exception:
                pass

            try:
                self.ui.coinNumber.setText(str(self.user_details.get("coin_count", 0)))
                self.ui.accountCoinsCount.setText(str(self.user_details.get("coin_count", 0)))
            except Exception:
                pass

            try:
                self.ui.selectConfigComboBox.clear()
                self.ui.selectConfigComboBox.setView(QtWidgets.QListView(self.ui.selectConfigComboBox))
                self.ui.selectConfigComboBox.view().setVerticalScrollBarPolicy(
                    QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
                )
                self.ui.selectConfigComboBox.setMaxVisibleItems(2) 

                configs = self.user_details.get("config_codes", []) or []
                for cfg in configs:
                    code_full = cfg.get("config_code", "")
                    display_name = code_full.split("#")[1] if "#" in code_full else code_full
                    gb = cfg.get("gb_left") or 0
                    days = cfg.get("days_left") or 0
                    
                    config_codes[display_name] = code_full

                    try:
                        days_val = float(days)
                    except Exception:
                        days_val = days
                    if isinstance(days_val, (int, float)) and days_val <= 0:
                        days = "expired"
                    self.ui.selectConfigComboBox.addItem(display_name)
                    i = self.ui.selectConfigComboBox.count() - 1
                    self.ui.selectConfigComboBox.setItemData(i, {"gb": gb, "days": days}, Qt.ItemDataRole.UserRole)

                all_configs_count = len(configs)
                expired_configs_count = 0
                for cfg in configs:
                    days = cfg.get("days_left") or 0
                    try:
                        days_val = float(days)
                    except Exception:
                        days_val = None
                    if isinstance(days_val, (int, float)) and days_val <= 0:
                        expired_configs_count += 1
                self.ui.accountAllConfigsCount.setText(str(all_configs_count))
                self.ui.accountExpiredConfigsCount.setText(str(expired_configs_count))

                self.ui.selectConfigComboBox.setItemDelegate(ConfigDelegateComboBox(self.ui.selectConfigComboBox))
                self.ui.selectConfigComboBox.setEditable(False)
            except Exception:
                pass
        else:
            try:
                self._show_toast(data, 3000)
            except Exception:
                pass

    def _connect_signals(self):
        try:
            self.ui.powerButton.clicked.connect(self.on_power_clicked)
        except Exception:
            pass

        self.ui.menuButton.clicked.connect(self.on_menu_clicked)
        self.ui.sideMenuHomeButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(0))
        self.ui.sideMenuAccountButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(1))
        self.ui.sideMenuBuyCoinsButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(4))
        self.ui.accountlogoutButton.clicked.connect(self.on_logout_clicked)
        self.ui.buyCoinsCounter.valueChanged.connect(self.on_counter_change)
        self.ui.buyCoinsBuyButton.clicked.connect(self.on_buycoin_clicked)

    def on_buycoin_clicked(self):
        url = f"https://t.me/{CONFIG['ADMIN_TELEGRAM_ID']}"
        webbrowser.open(url, new=2)

    def on_counter_change(self):
        if len(str(self.ui.buyCoinsCounter.value()*CONFIG['COIN_PRICE']))>5:
            self.ui.buyCoinsTomanUnitText.setGeometry(self.ui.buyCoinsTomanUnitText.x()+(10*(len(str(self.ui.buyCoinsCounter.value()*CONFIG['COIN_PRICE']))-5)),self.ui.buyCoinsTomanUnitText.y(),
                                                      self.ui.buyCoinsTomanUnitText.width(),self.ui.buyCoinsTomanUnitText.height())
        else:
            self.ui.buyCoinsTomanUnitText.setGeometry(self.toman_unit_x,self.ui.buyCoinsTomanUnitText.y(),
                                          self.ui.buyCoinsTomanUnitText.width(),self.ui.buyCoinsTomanUnitText.height())
        self.ui.buyCoinsEqualMoneyNumber.setFixedWidth(len(str(self.ui.buyCoinsCounter.value()*CONFIG['COIN_PRICE']))*10)
        self.ui.buyCoinsEqualMoneyNumber.setText(str(self.ui.buyCoinsCounter.value()*CONFIG['COIN_PRICE']))

    def on_power_clicked(self):
        current = self.ui.connectionStatusText.text()
        if current in ("Not Connected", "Disconnected") and self.ui.selectConfigComboBox.currentText() != "":
            self.power_button_fancy.set_state("connecting")
            self.power_button_fancy.setDisabled(True)
            self.ui.connectionStatusText.setText("Connecting...")
            self.ui.selectConfigComboBox.setDisabled(True)
            QtCore.QTimer.singleShot(2000, self._on_connected)

            self.xray_client = XrayClient(config_codes[self.ui.selectConfigComboBox.currentText()],set_system_proxy=True)
            self.xray_client.start()
        else:
            self.power_button_fancy.set_state("disconnected")
            self.ui.connectionStatusText.setText("Disconnected")
            self.power_button_fancy.setDisabled(False)
            self.ui.selectConfigComboBox.setDisabled(False)
            if self.ui.selectConfigComboBox.currentText() != "":
                self.xray_client.stop()
            else:
                pass

    def _on_connected(self):
        self.power_button_fancy.set_state("connected")
        self.ui.connectionStatusText.setText("Connected")
        self.power_button_fancy.setDisabled(False)
        self.ui.selectConfigComboBox.setDisabled(True)

    def on_menu_clicked(self):
        menu_btn = self.ui.menuButton
        side_menu = self.ui.sideMenu

        if not hasattr(self, "_menu_btn_initial_geom"):
            self._menu_btn_initial_geom = menu_btn.geometry()
        if not hasattr(self, "_side_menu_initial_geom"):
            self._side_menu_initial_geom = side_menu.geometry()

        menu_btn_geom = self._menu_btn_initial_geom
        side_menu_geom = self._side_menu_initial_geom

        offset = 100

        anim_menu = QPropertyAnimation(menu_btn, b"geometry")
        anim_side = QPropertyAnimation(side_menu, b"geometry")

        anim_menu.setDuration(350)
        anim_side.setDuration(350)
        anim_menu.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim_side.setEasingCurve(QEasingCurve.Type.OutQuad)

        if not self.menu_toggle:
            menu_btn_end = QtCore.QRect(menu_btn_geom.x() - offset, menu_btn_geom.y(), menu_btn_geom.width(), menu_btn_geom.height())
            side_menu_end = QtCore.QRect(side_menu_geom.x() - offset, side_menu_geom.y(), side_menu_geom.width(), side_menu_geom.height())
        else:
            menu_btn_end = QtCore.QRect(menu_btn_geom.x(), menu_btn_geom.y(), menu_btn_geom.width(), menu_btn_geom.height())
            side_menu_end = QtCore.QRect(side_menu_geom.x(), side_menu_geom.y(), side_menu_geom.width(), side_menu_geom.height())

        anim_menu.setStartValue(menu_btn.geometry())
        anim_menu.setEndValue(menu_btn_end)
        anim_side.setStartValue(side_menu.geometry())
        anim_side.setEndValue(side_menu_end)

        anim_menu.start()
        anim_side.start()

        menu_btn._anim = anim_menu
        side_menu._anim = anim_side

        self.menu_toggle = not self.menu_toggle

    def on_sidebutton_clicked(self, name):
        QtWidgets.QMessageBox.information(self, name, f"{name} clicked")

    def on_logout_clicked(self):
        try:
            self.ui.accountlogoutButton.setDisabled(True)
        except Exception:
            pass

        try:
            self._show_toast("Logging out...", 1200)
        except Exception:
            pass

        t = threading.Thread(target=self._perform_logout, daemon=True)
        t.start()

    def _perform_logout(self):
        ok = True
        msg = "Logged out"
        try:
            try:
                if hasattr(self, "xray_client") and self.xray_client is not None:
                    try:
                        self.xray_client.stop()
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                if 'manage_db' in globals() and manage_db is not None:
                    try:
                        manage_db.execute_database("DELETE FROM Auth;")
                    except Exception as e:
                        try:
                            conn = sqlite3.connect(manage_db.db_file)
                            cur = conn.cursor()
                            cur.execute("DELETE FROM Auth;")
                            conn.commit()
                            conn.close()
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                global config_codes
                config_codes.clear()
            except Exception:
                pass

            if ok:
                msg = "Logged out successfully"
        except Exception as e:
            ok = False
            msg = f"Logout error: {e}"

        try:
            self.logout_finished.emit(ok, str(msg))
        except Exception:
            pass

    def _on_logout_finished(self, ok: bool, msg: str):
        try:
            self.ui.accountlogoutButton.setDisabled(False)
        except Exception:
            pass

        try:
            self._show_toast(msg, 2000)
        except Exception:
            pass

        if ok:
            try:
                try:
                    login_window.show()
                except Exception:
                    pass
                try:
                    main_window.close()
                except Exception:
                    pass
            except Exception:
                pass
        else:
            pass

    def _show_toast(self, text: str, duration: int = 2500):
        toast = PopupToast(self, text=text, duration=duration)
        toast.show_toast()

class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_LoginWindow()
        self.ui.setupUi(self)

        self.product_name = CONFIG['PRODUCT_NAME']

        self.setWindowTitle(f"{self.product_name} - Login")

        QtGui.QFontDatabase.addApplicationFont(":/fonts/RobotoMono-Regular.ttf")
        QtGui.QFontDatabase.addApplicationFont(":/fonts/SFProDisplay-Regular.ttf")

        self._make_labels_clickable()
        self._apply_header_with_fancylabel()

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
            FancyLabel(parent=self.ui.userLogin, target_label=self.ui.headerText, text=self.product_name)
            FancyLabel(parent=self.ui.userLogin, target_label=self.ui.pTextLogin, text=self.ui.pTextLogin.text(), font_size=12)
        except Exception:
            pass
        try:
            FancyLabel(parent=self.ui.userRegister, target_label=self.ui.headerTextRegister, text=self.product_name)
            FancyLabel(parent=self.ui.userRegister, target_label=self.ui.pTextRegister, text=self.ui.pTextRegister.text(), font_size=13)
        except Exception:
            pass

    def validate_login(self) -> tuple[bool, str]:
        username = self.ui.usernameLineEdit.text().strip()
        pwd = self.ui.passwordLineEdit.text()
        if not username:
            return False, "Username is required"
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

        username = self.ui.usernameLineEdit.text().strip()
        password = self.ui.passwordLineEdit.text()
        login_window.ui.loginButton.setDisabled(True)
        ok , msg = api_calls.login(username=username,password=password)
        if ok:
            try:
                main_window.refresh_user_data()
            except:
                pass
            main_window.show()
            login_window.ui.loginButton.setDisabled(False)
            return login_window.close()
        login_window.ui.loginButton.setDisabled(False)
        return self._show_toast(msg, duration=1800)

    def on_submit_clicked(self):
        ok, msg = self.validate_submit()
        if not ok:
            self._show_toast(msg)
            return

        username = self.ui.usernameLineEditRegister.text().strip()
        email = self.ui.emailLineEditRegister.text().strip()
        password = self.ui.passwordLineEditRegister.text()
        login_window.ui.submitButton.setDisabled(True)

        ok , msg = api_calls.register(username=username,email=email,password=password)
        if ok:
            email_verify_window.set_data(email,username,password)
            email_verify_window.show()
            login_window.ui.submitButton.setDisabled(False)
            return login_window.close()
        login_window.ui.submitButton.setDisabled(False)
        return self._show_toast(msg, duration=1800)

    def _show_toast(self, text: str, duration: int = 2500):
        toast = PopupToast(self, text=text, duration=duration)
        toast.show_toast()

class VerifyEmailWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_VerifyEmailWindow()
        self.ui.setupUi(self)

        self._apply_header_with_fancylabel()

        self.product_name = CONFIG['PRODUCT_NAME']

        self.setWindowTitle(f"{self.product_name} - verify your email address")

        self.ui.verifyButton.clicked.connect(self.on_verify_clicked)
        self.ui.backToLoginButton.clicked.connect(self.on_back_to_login_clicked)
        self.ui.resendCodeButton.clicked.connect(self.on_resend_code_clicked)

        self.ui.headerText.setText(self.product_name)

    def _apply_header_with_fancylabel(self):
        try:
            FancyLabel(parent=self, target_label=self.ui.headerText, text=self.product_name)
        except Exception:
            pass
        try:
            FancyLabel(parent=self, target_label=self.ui.pTextVerify, text=self.ui.pTextVerify.text(),font_size=13)
        except Exception:
            pass

    def validate_code(self):
        code = self.ui.codeEditLine.text().strip()
        if not code.isdigit():
            return False, "plase enter a valid code"
        return True, ""

    def on_verify_clicked(self):
        ok, msg = self.validate_code()
        if ok:
            code = self.ui.codeEditLine.text().strip()
            self.ui.verifyButton.setDisabled(True)
            ok , msg = api_calls.send_verifycation_code(self.email,code)
            if ok:
                ok , msg = api_calls.login(self.username,self.password)
                if ok:
                    try:
                        main_window.refresh_user_data()
                    except:
                        pass
                    main_window.show()
                    self.ui.verifyButton.setDisabled(False)
                    return email_verify_window.close()
                self.ui.verifyButton.setDisabled(False)
                return self._show_toast(msg,2000)
            self.ui.verifyButton.setDisabled(False)
            return self._show_toast(msg,2000)
        return self._show_toast(msg, 2000)

    def on_back_to_login_clicked(self):
        login_window.show()
        return email_verify_window.close()

    def on_resend_code_clicked(self):
        self.ui.resendCodeButton.setDisabled(True)
        ok ,msg = api_calls.resend_verification_code(self.email)
        if ok:
            self._show_toast(msg, 2000)
            return self.ui.resendCodeButton.setDisabled(False)
        self._show_toast(msg, 2000)
        return self.ui.resendCodeButton.setDisabled(False)

    def set_data(self,email,username,password):
        self.email = email
        self.username = username
        self.password = password

    def _show_toast(self, text: str, duration: int = 2500):
        toast = PopupToast(self, text=text, duration=duration)
        toast.show_toast()

if __name__ == "__main__":
    
    manage_db = ManageDatabase()
    manage_db.init_db()

    backaddr_full = manage_db.get_backaddr()
    backaddr_full = f"http://{backaddr_full['sub']}.{backaddr_full['name']}.{backaddr_full['tld']}:{backaddr_full['port']}"

    config_codes = {}

    api_calls = ApiCalls(backaddr_full)

    app = QtWidgets.QApplication(sys.argv)

    main_window = MainAppWindow()
    login_window = LoginWindow()
    email_verify_window = VerifyEmailWindow()

    if api_calls.login_needed():
        login_window.show()
    else:
        main_window.show()

    sys.exit(app.exec())
