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
from PyQt6.QtGui import QColor, QCursor, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QStyle, QApplication

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
from modules.path_helpers import get_path

from core.handlers.manager import XrayClient, set_proxy_exceptions

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

        self.tray_menu = QMenu(self)
        self.tray_action_toggle = QAction("Show/Hide", self)
        self.tray_action_exit = QAction("Exit", self)
        self.tray_action_toggle.triggered.connect(self.toggle_visibility)
        self.tray_action_exit.triggered.connect(self.exit_app)

        self.tray_menu.addAction(self.tray_action_toggle)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.tray_action_exit)

        tray_icon = QtGui.QIcon(str(get_path("assets", "icons", CONFIG['TRAYICON_NAME'])))
        self.tray_icon = QSystemTrayIcon(tray_icon, parent=self)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.setToolTip(f"{self.product_name}")
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        self.tray_icon.hide()
        self.tray_enabled = False

        QtWidgets.QApplication.setQuitOnLastWindowClosed(False)

        window_icon = QtGui.QIcon(str(get_path("assets", "icons", CONFIG['TRAYICON_NAME'])))
        self.setWindowIcon(window_icon)

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
            configs = []
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
        self.buyconfig_header = FancyLabel(self.ui.buyConfigsTab, self.ui.buyConfigsHeaderText, self.product_name)
        self.settings_header = FancyLabel(self.ui.settingsTab, self.ui.settingsHeaderText, self.product_name)
        self.myconfigs_header = FancyLabel(self.ui.configsTab, self.ui.myConfigsHeaderText, self.product_name)

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

        request_plans_success , request_plans_content = api_calls.get_plans()
        if request_plans_success:
            self.populate_buyconfigs_from_data(request_plans_content)
        else:
            self._show_toast(request_plans_content,3000)

        addresses = manage_db.get_exclusive_addresses()
        if addresses is not None:
            init_content = "\n".join(addresses)
            self.ui.settingsProxyExclusivesTextEdit.setPlainText(init_content)
            set_proxy_exceptions(addresses)
            
        self.init_myconfigs(configs)

        self.ui.menuButton.raise_()
        self.ui.sideMenu.raise_()

        self.menu_toggle = False

    def toggle_visibility(self):
        if not getattr(self, "tray_enabled", False):
            return
        try:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
        except Exception:
            pass

    def on_tray_activated(self, reason):
        if not getattr(self, "tray_enabled", False):
            return

        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            try:
                self.tray_menu.exec(QCursor.pos())
            except Exception:
                pass

    def closeEvent(self, event):    
        if getattr(self, "_allow_close", False):
            event.accept()
            return

        event.ignore()
        self.hide()

    def force_close(self):
        try:
            self._allow_close = True
            try:
                self.tray_icon.hide()
            except Exception:
                pass
            self.close()
            QtWidgets.QApplication.quit()
        except Exception:
            try:
                QtWidgets.QApplication.quit()
            except Exception:
                pass

    def enable_tray(self):
        try:
            self._allow_close = False
            self.tray_icon.setVisible(True)
            self.tray_icon.show()
            self.tray_enabled = True
            QtWidgets.QApplication.setQuitOnLastWindowClosed(False)
        except Exception:
            pass

    def disable_tray(self):
        try:
            self.tray_icon.hide()
            self.tray_icon.setVisible(False)
            self.tray_enabled = False
        except Exception:
            pass

    def close_for_logout(self):
        try:
            self.disable_tray()
            self._allow_close = True
            self.close()
        except Exception:
            pass

    def exit_app(self):
        try:
            try:
                if hasattr(self, "xray_client") and self.xray_client is not None:
                    self.xray_client.stop()
            except Exception:
                pass
            self._allow_close = True
            try:
                self.tray_icon.hide()
            except Exception:
                pass
            self.close()
        finally:
            try:
                QtWidgets.QApplication.quit()
            except Exception:
                pass

    def init_myconfigs(self,data):

        configs = data if isinstance(data, (list, tuple)) else (data or [])

        for cfg in configs:
            try:
                code_full = cfg.get("config_code") if isinstance(cfg, dict) else None
                display_name = cfg.get("display_name") if isinstance(cfg, dict) else None
                if not display_name and code_full:
                    display_name = code_full.split("#")[1] if "#" in code_full else code_full
                if not display_name:
                    display_name = cfg.get("name") if isinstance(cfg, dict) else str(cfg)

                days = cfg.get("days_left", 0) if isinstance(cfg, dict) else 0
                try:
                    days_val = float(days)
                except Exception:
                    days_val = days
                if isinstance(days_val, (int, float)) and days_val <= 0:
                    days = "expired"
                gb = cfg.get("gb_left", 0) if isinstance(cfg, dict) else 0
                config_code_for_button = code_full or cfg.get("config_code") if isinstance(cfg, dict) else None

                safe_name = self._sanitize_name(display_name)
                frame_obj_name = f"myconfigs_frame_{safe_name}"

                frame = QtWidgets.QFrame(self.ui.myconfigs_mainContainer.parentWidget())
                self.ui.myconfigs_mainContainer.addWidget(frame)
                frame.setObjectName(frame_obj_name)
                frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
                frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
                frame.setMinimumHeight(150)
                frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)

                root_layout = QtWidgets.QVBoxLayout(frame)
                root_layout.setSpacing(8)

                label_container = QtWidgets.QHBoxLayout()
                label_container.setSpacing(6)

                lbl_name = QtWidgets.QLabel(frame)
                lbl_name.setObjectName(f"myconfigs_frame_{safe_name}_configName")
                lbl_name.setText(str(display_name))
                lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

                lbl_days = QtWidgets.QLabel(frame)
                lbl_days.setObjectName(f"myconfigs_frame_{safe_name}_daysLeft")
                lbl_days.setText(f"Days Left: {days}")
                lbl_days.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

                lbl_gb = QtWidgets.QLabel(frame)
                lbl_gb.setObjectName(f"myconfigs_frame_{safe_name}_gbLeft")
                lbl_gb.setText(f"GB Left: {gb}")
                lbl_gb.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

                try:
                    cons_font = QtGui.QFont("Consolas", 9)
                    cons_font.setBold(True)
                    lbl_name.setFont(cons_font)
                    lbl_days.setFont(cons_font)
                    lbl_gb.setFont(cons_font)
                except Exception:
                    pass

                label_container.addWidget(lbl_name)
                label_container.addWidget(lbl_days)
                label_container.addWidget(lbl_gb)

                button_container = QtWidgets.QHBoxLayout()
                button_container.setSpacing(6)

                connect_btn = QtWidgets.QPushButton(frame)
                connect_btn.setObjectName(f"myconfigs_frame_{safe_name}_connectBtn")
                connect_btn.setText("Connect")
                connect_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                connect_btn.clicked.connect(lambda _checked, display_name=display_name, code=config_codes[display_name]: self._myconfigs_connect(display_name, code))

                #delete_btn = QtWidgets.QPushButton(frame)
                #delete_btn.setObjectName(f"myconfigs_frame_{safe_name}_deleteBtn")
                #delete_btn.setText("Delete")
                #delete_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

                button_container.addWidget(connect_btn)
                #button_container.addWidget(delete_btn)

                root_layout.addLayout(label_container)
                root_layout.addLayout(button_container)

                connect_id=connect_btn.objectName()
                delete_id="None"#delete_btn.objectName()

                style = f"""
                    QFrame {{
                        background-color: #0f172a;
                        border-radius: 12px;
                        border: 1px solid rgba(94, 234, 212, 0.6);
                        min-height:150px;
                    }}

                    QFrame:hover{{
                        background-color: rgb(21, 34, 58);
                        border: 1px solid rgba(59,130,246,220);
                    }}

                    QLabel{{
                        min-height:65px;
                        max-height:65px;
                    }}

                    QPushButton#{connect_id} {{
                        background-color: #059669;
                        color: #f8fafc;
                        border-radius: 10px;
                        padding: 10px 18px;
                        font-weight: bold;
                        border: 2px solid #047857;
                        border-bottom: 4px solid #065f46;
                        outline: none;
                        min-width: 90px;
                        max-height: 20px;
                    }}
                    QPushButton#{connect_id}:hover {{
                        background-color: #10b981;
                        color: white;
                    }}
                    QPushButton#{connect_id}:pressed {{
                        background-color: #047857;
                        border: 2px solid #065f46;
                        border-top: 4px solid #065f46;
                        padding-top: 12px;
                        padding-bottom: 8px;
                    }}

                    QPushButton#{delete_id} {{
                        background-color: #b91c1c;
                        color: #f8fafc;
                        border-radius: 10px;
                        padding: 10px 18px;
                        font-weight: bold;
                        border: 2px solid #7f1d1d;
                        border-bottom: 4px solid #450a0a;
                        outline: none;
                        min-width: 90px;
                        max-height: 20px;
                    }}
                    QPushButton#{delete_id}:hover {{
                        background-color: #dc2626;
                        color: white;
                    }}
                    QPushButton#{delete_id}:pressed {{
                        background-color: #991b1b;
                        border: 2px solid #450a0a;
                        border-top: 4px solid #450a0a;
                        padding-top: 12px;
                        padding-bottom: 8px;
                    }}
                """
                try:
                    frame.setStyleSheet(style)
                except Exception:
                    pass

                self.ui.myconfigs_mainContainer.addWidget(frame)

            except Exception as e:
                print(e)
                try:
                    self._show_toast(f"Error creating config frame: {e}", 20000)
                except Exception:
                    pass

    def _myconfigs_connect(self, display_name: str, config_code: str):
        try:
            if not config_code:
                return self._show_toast("No config code available", 1800)

            current = self.ui.connectionStatusText.text()
            if current in ("Not Connected", "Disconnected"):
                self.power_button_fancy.set_state("connecting")
                self.power_button_fancy.setDisabled(True)
                self.ui.connectionStatusText.setText("Connecting...")
                self.ui.selectConfigComboBox.setDisabled(True)
                index = self.ui.selectConfigComboBox.findText(display_name, QtCore.Qt.MatchFlag.MatchExactly)
                if index != -1:
                    self.ui.selectConfigComboBox.setCurrentIndex(index)
                QtCore.QTimer.singleShot(2000, self._on_connected)
                try:
                    self.xray_client = XrayClient(config_code, set_system_proxy=True)
                    self.xray_client.start()
                except Exception:
                    pass
                return self.ui.tabWidget.setCurrentIndex(0)
            else:
                return self._show_toast("You already connected. Please disconnect first.")
        except Exception as e:
            try:
                self._show_toast(f"Connect error: {e}", 2000)
            except Exception:
                pass

    def _sanitize_name(self, name: str) -> str:
        import re
        if not name:
            return "unnamed"
        s = re.sub(r"[^0-9a-zA-Z]+", "_", str(name))
        return s.strip("_") or "unnamed"

    def populate_buyconfigs_from_data(self, data: list):

        frame_stylesheet = """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,6),
                    stop:0.55 rgba(255,255,255,3),
                    stop:1 rgba(0,0,0,14));
                border: 1px solid rgba(17,186,189,140); 
                border-radius: 12px;
                padding: 0px;
                color:white;
            }
            QFrame::indicator {}
            QLabel { 
                border: 1px solid rgba(17, 186, 189, 255);
                border-radius: 8px;
                font-weight: 600; font-size: 13px; 
            }
            QPushButton {
                background-color: #059669;
                color: #f8fafc;
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: bold;
                border: 2px solid #047857; 
                border-bottom: 4px solid #065f46;
                outline: none;
            }
            QPushButton:hover {
                background-color: #10b981;
                color: white;
            }
            QPushButton:pressed {
                background-color: #047857;
                border: 2px solid #065f46;
                border-top: 4px solid #065f46;
                padding-top: 12px;
                padding-bottom: 8px;
            }
        """ 
        for idx in range(len(data['plans'])):
            plan_id = data['plans'][idx].get("id", idx)
            plan_name = data['plans'][idx].get("plan_name", "Unknown Plan")
            plan_usage = data['plans'][idx].get("usage", "")
            plan_time = data['plans'][idx].get("time", "")
            plan_price = data['plans'][idx].get("price", "")
            number_of_users = data['plans'][idx].get("number_of_users","")

            frame = QtWidgets.QFrame(self.ui.scrollAreaWidgetContents)
            frame.setObjectName(f"buy_frame_{plan_id}")
            frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
            frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
            frame.setMinimumHeight(250)
            frame.setMinimumWidth(100)
            frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
            frame.setStyleSheet(frame_stylesheet)

            vbox = QtWidgets.QVBoxLayout(frame)
            vbox.setContentsMargins(10, 8, 10, 8)
            vbox.setSpacing(6)

            name_lbl = QtWidgets.QLabel(frame)
            name_lbl.setObjectName(f"plan_name_lbl_{plan_id}")
            name_lbl.setText(f"Plan Name : {plan_name}")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            price_lbl = QtWidgets.QLabel(frame)
            price_lbl.setObjectName(f"plan_price_lbl_{plan_id}")
            price_lbl.setText(f"Plan Price : {plan_price}")
            price_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            usage_lbl = QtWidgets.QLabel(frame)
            usage_lbl.setObjectName(f"plan_usage_lbl_{plan_id}")
            usage_lbl.setText(f"Plan Usage : {plan_usage}GB")
            usage_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            time_lbl = QtWidgets.QLabel(frame)
            time_lbl.setObjectName(f"plan_time_lbl_{plan_id}")
            time_lbl.setText(f"Plan Time : {plan_time} month")
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            usersnum_lbl = QtWidgets.QLabel(frame)
            usersnum_lbl.setObjectName(f"plan_usersnum_lbl_{plan_id}")
            usersnum_lbl.setText(f"Plan Number Of Users : {number_of_users}")
            usersnum_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            buy_btn = QtWidgets.QPushButton(frame)
            buy_btn.setObjectName(f"buy_btn_{plan_id}")
            buy_btn.setText("Buy")
            buy_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            buy_btn.clicked.connect(lambda _checked, plan=data['plans'][idx]: self.on_buyconfig_clicked(plan))

            vbox.addWidget(name_lbl)
            vbox.addWidget(price_lbl)
            vbox.addWidget(usage_lbl)
            vbox.addWidget(time_lbl)
            vbox.addWidget(usersnum_lbl)
            vbox.addWidget(buy_btn)

            self.ui.verticalLayout.addWidget(frame)

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
            coin_count = str(self.user_details.get("coin_count", 0))
            try:
                self.ui.usernameText.setFixedWidth(max(1, len(username)) * 10)
                self.ui.usernameText.setText(username)
                self.ui.accountUsernameText.setText(username)
                self.ui.accountEmailText.setText(email)
            except Exception:
                pass

            try:
                self.ui.coinNumber.setText(coin_count)
                self.ui.accountCoinsCount.setText(coin_count)
                self.ui.buyCoinsYourCoinsText.setText(f"You Have : {coin_count} Coins")
                if hasattr(self, "buycoin_your_coins"):
                    self.buycoin_your_coins.setText(f"You Have : {coin_count} Coins")
            except Exception:
                pass

            # Update selectConfigComboBox
            try:
                self.ui.selectConfigComboBox.clear()
                self.ui.selectConfigComboBox.setView(QtWidgets.QListView(self.ui.selectConfigComboBox))
                self.ui.selectConfigComboBox.view().setVerticalScrollBarPolicy(
                    QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
                )
                self.ui.selectConfigComboBox.setMaxVisibleItems(2)

                configs = self.user_details.get("config_codes", []) or []
                global config_codes
                config_codes.clear()
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

            try:
                container = self.ui.myconfigs_mainContainer
                while container.count():
                    item = container.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.setParent(None)
                        widget.deleteLater()
                self.init_myconfigs(configs)
            except Exception:
                pass

            try:
                plans_ok, plans_data = api_calls.get_plans()
                if plans_ok:
                    vlayout = self.ui.verticalLayout
                    while vlayout.count():
                        item = vlayout.takeAt(0)
                        widget = item.widget()
                        if widget is not None:
                            widget.setParent(None)
                            widget.deleteLater()
                    self.populate_buyconfigs_from_data(plans_data)
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
        self.ui.sideMenuBuyConfigsButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(3))
        self.ui.sideMenuSettingsButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(5))
        self.ui.sideMenuConfigsButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(2))
        self.ui.accountlogoutButton.clicked.connect(self.on_logout_clicked)
        self.ui.buyCoinsCounter.valueChanged.connect(self.on_counter_change)
        self.ui.buyCoinsBuyButton.clicked.connect(self.on_buycoin_clicked)
        self.ui.settingsProxyExclusivesApplyButton.clicked.connect(self.settings_exclusive_proxy_apply_clicked)

    def settings_exclusive_proxy_apply_clicked(self):
        addresses = self.ui.settingsProxyExclusivesTextEdit.toPlainText().split("\n")
        manage_db.set_exclusive_addresses(addresses)
        addresses = manage_db.get_exclusive_addresses()
        if addresses is not None:
            set_proxy_exceptions(addresses)
            return self._show_toast("Exclusive addresses applyed successfully ✅")
        return self._show_toast("There is no address to  set as exlusive", 3000)

    def on_buyconfig_clicked(self, plan: dict):
        try:
            plan_id = plan.get("id", plan.get("plan_id", "Unknown"))
            name = plan.get("plan_name", plan.get("name", "Unknown"))
            usage = plan.get("plan_usage", plan.get("usage", "N/A"))
            time_days = plan.get("plan_time", plan.get("time", "N/A"))
            price = plan.get("plan_price", plan.get("price", "N/A"))
            number_of_users = plan.get("number_of_users", "")

            lines = [
                f"📦  Name: {name}",
                f"📊  Usage: {usage} GB",
                f"⏳  Time: {time_days} month",
                f"💰  Price: {price} coins",
            ]
            if number_of_users not in (None, "", "N/A"):
                lines.append(f"👥  Users: {number_of_users}")

            body = "\n".join(lines)
            body += "\n\nAre you sure you want to buy this plan?"

            resp = QtWidgets.QMessageBox.question(
                self,
                "Confirm Purchase",
                body,
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )

            if resp == QtWidgets.QMessageBox.StandardButton.Yes:
                purchase_plan_status, purchase_plan_result = api_calls.buy_plan(plan_id)
                if purchase_plan_status:
                    code_full = purchase_plan_result['details'].get("config_code", "")
                    display_name = code_full.split("#")[1] if "#" in code_full else code_full
                    gb = purchase_plan_result['details'].get("usage") or 0
                    days = purchase_plan_result['details'].get("time")*30 or 0
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

                    self.ui.coinNumber.setText(str(int(self.ui.coinNumber.text())-purchase_plan_result['details'].get("price")))
                    self.ui.accountCoinsCount.setText(str(int(self.ui.accountCoinsCount.text())-purchase_plan_result['details'].get("price")))
                    self.ui.accountAllConfigsCount.setText(str(int(self.ui.accountAllConfigsCount.text())+1))

                    new_config = {
                        "config_code": code_full,
                        "display_name": display_name,
                        "days_left": days,
                        "gb_left": gb
                    }
                    self.init_myconfigs([new_config])

                    return self._show_toast("Plan Successfully purchased ✅")
                return self._show_toast(purchase_plan_result)
            
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Error in on_buyconfig_clicked:\n{e}")

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
                    main_window.disable_tray()
                    main_window.close_for_logout()
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

        self._programmatic_close = False

        window_icon = QtGui.QIcon(str(get_path("assets", "icons", CONFIG['TRAYICON_NAME'])))
        self.setWindowIcon(window_icon)

    def closeEvent(self, event):
        if getattr(self, "_programmatic_close", False):
            self._programmatic_close = False
            event.accept()
            return
        try:
            try:
                if 'main_window' in globals() and getattr(main_window, "tray_icon", None):
                    try:
                        main_window.tray_icon.hide()
                    except Exception:
                        pass
            except Exception:
                pass
        finally:
            event.accept()
            QApplication.quit()

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
            main_window.enable_tray() 
            login_window.ui.loginButton.setDisabled(False)
            login_window._programmatic_close = True
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
            login_window._programmatic_close = True
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

        self._programmatic_close = False

        window_icon = QtGui.QIcon(str(get_path("assets", "icons", CONFIG['TRAYICON_NAME'])))
        self.setWindowIcon(window_icon)

    def closeEvent(self, event):
        if getattr(self, "_programmatic_close", False):
            self._programmatic_close = False
            event.accept()
            return
        try:
            try:
                if 'main_window' in globals() and getattr(main_window, "tray_icon", None):
                    try:
                        main_window.tray_icon.hide()
                    except Exception:
                        pass
            except Exception:
                pass
        finally:
            event.accept()
            QApplication.quit()

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
                    main_window.enable_tray() 
                    self.ui.verifyButton.setDisabled(False)
                    email_verify_window._programmatic_close = True
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
        main_window.enable_tray() 

    sys.exit(app.exec())
