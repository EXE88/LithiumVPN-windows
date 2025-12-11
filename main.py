import resources_rc
import sys
import threading
import sqlite3
import webbrowser
from configuration import CONFIG

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal, QEasingCurve, QPropertyAnimation, Qt
from PyQt6.QtGui import QCursor, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from design.dotpy.main_window import Ui_MainWindow
from design.dotpy.login_window import Ui_Form as Ui_LoginWindow
from design.dotpy.verify_email_window import Ui_Form as Ui_VerifyEmailWindow

from custome_widgets.fancy_label import FancyLabel, FancyLabelBetter
from custome_widgets.round_line import RoundedLine
from custome_widgets.popup_toast import PopupToast
from custome_widgets.fancy_round_button import FancyRoundButton
from custome_widgets.config_delegate_comboBox import ConfigDelegateComboBox
from custome_widgets.rgb_label import RGBLabel
from custome_widgets.fancy_messagebox import ThemedMessageBox

from modules.database import ManageDatabase
from modules.api_calls import ApiCalls
from modules.path_helpers import get_path
from modules.qrcode_generator import ShareConfigDialog
from core.handlers.manager import XrayClient, set_proxy_exceptions

class MainAppWindow(QtWidgets.QMainWindow):

    logout_finished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()

        # ---------- UI and layout setup ----------
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Internal initialization
        self._setup_ui()
        self._connect_signals()

        # system tray initialization
        self._init_tray()

        # Signals
        self.logout_finished.connect(self._handle_logout_finished)

        # Prevent quitting when last window closed (we use tray)
        QtWidgets.QApplication.setQuitOnLastWindowClosed(False)

    # -------------------- helper setup methods --------------------

    def _setup_ui(self):
        """Initial load: populate user info, widgets, and tab content."""

        # Global settings
        self.product_name = CONFIG['PRODUCT_NAME']
        self.admin_telegram = CONFIG['ADMIN_TELEGRAM_ID']
        self.menu_toggle = False

        # Window icon and title
        window_icon = QtGui.QIcon(str(get_path("assets", "icons", CONFIG['TRAYICON_NAME'])))
        self.setWindowIcon(window_icon)
        self.setWindowTitle(self.product_name)

        #load fonts
        QtGui.QFontDatabase.addApplicationFont(":/fonts/RobotoMono-Regular.ttf")
        QtGui.QFontDatabase.addApplicationFont(":/fonts/SFProDisplay-Regular.ttf")

        # Fetch user info
        user_ok, user_data = api_calls.get_user()
        if user_ok and isinstance(user_data, dict):
            self._populate_user_info(user_data)
        else:
            # On error, set defaults and show toast
            self.coin_count = 0
            self._show_toast(user_data, 3000, "error")

        # Try to hide optional widget if present
        try:
            self.ui.continueProfileLine.hide()
        except Exception:
            pass

        # Decorative vertical rounded line
        self.rounded_line = RoundedLine(
            parent=self.ui.homeTab,
            x=25.5, y=65,
            length=71.7, thickness=2.3,
            color=QtGui.QColor(230, 230, 230),
            vertical=True
        )

        # Fancy headers for tabs
        self.home_header = FancyLabel(self.ui.homeTab, self.ui.headerText, self.product_name)
        self.account_header = FancyLabel(self.ui.accountTab, self.ui.accountHeaderText, self.product_name)
        self.buycoin_header = FancyLabel(self.ui.buyCoinsTab, self.ui.buyCoinsHeaderText, self.product_name)
        self.buyconfig_header = FancyLabel(self.ui.buyConfigsTab, self.ui.buyConfigsHeaderText, self.product_name)
        self.settings_header = FancyLabel(self.ui.settingsTab, self.ui.settingsHeaderText, self.product_name)
        self.myconfigs_header = FancyLabel(self.ui.configsTab, self.ui.myConfigsHeaderText, self.product_name)

        # Admin Telegram ID in buy-coins tab
        self.ui.buyCoinsAdminID.setText(self.admin_telegram)
        self.admin_telegram_label = RGBLabel(self.ui.buyCoinsTab, self.ui.buyCoinsAdminID, self.admin_telegram)

        # Buy-coins description with fancy style
        self.buycoin_description = FancyLabelBetter(
            self.ui.buyCoinsTab,
            self.ui.buyCoinsDescription,
            self.ui.buyCoinsDescription.text(),
            glow_color=(255, 215, 0, 200),
            shadow_color=(184, 134, 11, 160),
            header_color_stop0=(212, 175, 55, 255),
            header_color_stop1=(255, 223, 132, 255)
        )

        # Remove legacy power widgets if present
        self._cleanup_legacy_power_widgets()

        # Create the circular main power button
        self._create_power_button()

        # Fetch plans and populate buy-configs tab
        plans_ok, plans_data = api_calls.get_plans()
        if plans_ok:
            self.populate_buy_plans(plans_data)
        else:
            self._show_toast(plans_data, 3000, "error")

        # Load proxy exception addresses from local DB
        addresses = manage_db.get_exclusive_addresses()
        if addresses is not None:
            init_content = "\n".join(addresses)
            self.ui.settingsProxyExclusivesTextEdit.setPlainText(init_content)
            set_proxy_exceptions(addresses)

        # Initialize my-configs list
        configs = user_data.get("config_codes", []) if (user_ok and isinstance(user_data, dict)) else []
        self.load_myconfigs(configs)

        # Ensure menu button and side menu are on top
        self.ui.menuButton.raise_()
        self.ui.sideMenu.raise_()

    def _connect_signals(self):
        """Connect widget signals to handlers."""

        self.ui.powerButton.clicked.connect(self.on_power_clicked)
        self.ui.menuButton.clicked.connect(self.on_menu_clicked)
        self.ui.sideMenuHomeButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(0))
        self.ui.sideMenuAccountButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(1))
        self.ui.sideMenuBuyCoinsButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(4))
        self.ui.sideMenuBuyConfigsButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(3))
        self.ui.sideMenuSettingsButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(5))
        self.ui.sideMenuConfigsButton.clicked.connect(lambda: self.ui.tabWidget.setCurrentIndex(2))
        self.ui.accountlogoutButton.clicked.connect(self.on_logout_clicked)
        self.ui.buyCoinsBuyButton.clicked.connect(self.on_buycoin_clicked)
        self.ui.settingsProxyExclusivesApplyButton.clicked.connect(self.settings_exclusive_proxy_apply_clicked)

    def _init_tray(self):
        """Create tray icon and menu."""
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

        # Hidden by default; call enable_tray() to show
        self.tray_icon.hide()
        self.tray_enabled = False

    # -------------------- internal helpers --------------------

    def _populate_user_info(self, user_data: dict):
        """Set widgets based on user information."""
        self.user_details_status = True
        self.user_details = user_data

        self.coin_count = str(user_data.get("coin_count", 0))
        username = user_data.get("username", "") or ""
        email = user_data.get("email", "") or ""

        self.ui.usernameText.setFixedWidth(max(1, len(username)) * 10)
        self.ui.usernameText.setText(username)
        self.ui.accountUsernameText.setText(username)
        self.ui.accountEmailText.setText(email)

        self.ui.coinNumber.setText(str(user_data.get("coin_count", 0)))
        self.ui.accountCoinsCount.setText(str(user_data.get("coin_count", 0)))

        # Configure the config combobox
        configs = user_data.get("config_codes", []) or []
        self._setup_config_combobox(configs)

    def _refresh_userdata(self):
        """Fetch fresh user data from server and update UI elements (configs, myconfigs, plans)."""
        try:
            status, data = api_calls.get_user()
        except Exception as e:
            status, data = False, f"Error fetching user: {e}"

        if status and isinstance(data, dict):
            self.user_details_status = status
            self.user_details = data

            username = self.user_details.get("username", "") or ""
            email = self.user_details.get("email", "") or ""
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
            except Exception:
                pass

            # Update selectConfigComboBox and config_codes mapping
            try:
                configs = self.user_details.get("config_codes", []) or []
                try:
                    self._setup_config_combobox(configs)
                except Exception:
                    pass
            except Exception:
                pass

            # Rebuild myconfigs UI
            try:
                container = self.ui.myconfigs_mainContainer
                try:
                    while container.count():
                        item = container.takeAt(0)
                        widget = item.widget()
                        if widget is not None:
                            widget.setParent(None)
                            widget.deleteLater()
                except Exception:
                    pass
                try:
                    self.load_myconfigs(configs)
                except Exception:
                    pass
            except Exception:
                pass

            # Refresh available plans for buy-configs
            try:
                plans_ok, plans_data = api_calls.get_plans()
                if plans_ok:
                    try:
                        vlayout = self.ui.verticalLayout
                        while vlayout.count():
                            item = vlayout.takeAt(0)
                            widget = item.widget()
                            if widget is not None:
                                widget.setParent(None)
                                widget.deleteLater()
                    except Exception:
                        pass
                    try:
                        self.populate_buy_plans(plans_data)
                    except Exception:
                        pass
            except Exception:
                pass

        else:
            try:
                self._show_toast(data, 3000, "error")
            except Exception:
                pass

    def _setup_config_combobox(self, configs: list):
        """Fill selectConfigComboBox and maintain map of config_codes."""
        self.ui.selectConfigComboBox.clear()
        self.ui.selectConfigComboBox.setView(QtWidgets.QListView(self.ui.selectConfigComboBox))
        self.ui.selectConfigComboBox.view().setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.ui.selectConfigComboBox.setMaxVisibleItems(2)

        global config_codes
        # Ensure config_codes dict exists
        if 'config_codes' not in globals():
            globals()['config_codes'] = {}
        config_codes.clear()

        for cfg in configs:
            if not isinstance(cfg, dict):
                continue
            code_full = cfg.get("config_code", "") or ""
            display_name = code_full.split("#")[1] if "#" in code_full else code_full
            gb = cfg.get("gb_left") or 0
            days = cfg.get("days_left") or 0
            server = cfg.get("server", "")

            config_codes[display_name] = code_full

            days = self.format_days_left(days)

            self.ui.selectConfigComboBox.addItem(f"{display_name} ({server})")
            i = self.ui.selectConfigComboBox.count() - 1
            self.ui.selectConfigComboBox.setItemData(i, {"gb": gb, "days": days}, Qt.ItemDataRole.UserRole)

        all_configs_count = len(configs)
        expired_configs_count = sum(
            1 for cfg in configs if self._is_expired(cfg.get("days_left", 0))
        )
        self.ui.accountAllConfigsCount.setText(str(all_configs_count))
        self.ui.accountExpiredConfigsCount.setText(str(expired_configs_count))

        self.ui.selectConfigComboBox.setItemDelegate(ConfigDelegateComboBox(self.ui.selectConfigComboBox))
        self.ui.selectConfigComboBox.setEditable(False)

    def format_days_left(self, days_value):
        """Format days_left value and convert non-positive values to 'expired'."""
        try:
            days_num = float(days_value)
        except Exception:
            days_num = days_value

        if isinstance(days_num, (int, float)) and days_num <= 0:
            return "expired"
        return days_value

    def _is_expired(self, days_value) -> bool:
        """Return whether days_value indicates expiration."""
        try:
            days_num = float(days_value)
            return days_num <= 0
        except Exception:
            return False

    def _cleanup_legacy_power_widgets(self):
        """Try to remove legacy powerButtonBase and powerButton widgets if present."""
        # Explicitly remove powerButtonBase on ui
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

        # Search among all children for legacy items
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

    def _create_power_button(self):
        """Create and configure the circular FancyRoundButton for power control."""
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

    def _clear_layout_widgets(self, layout):
        """Remove and delete all widgets from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    # -------------------- myconfigs and buyconfigs management --------------------

    def load_myconfigs(self, data):
        """Create my-configs cards from the provided data list."""
        configs = data if isinstance(data, (list, tuple)) else (data or [])
        for cfg in configs:
            try:
                self._create_config_card(cfg)
            except Exception as e:
                try:
                    self._show_toast(f"Error creating config frame: {e}", 20000, "error")
                except Exception:
                    pass

    def _create_config_card(self, cfg):
        """Create a frame for a single config item."""
        # Extract information
        code_full = cfg.get("config_code") if isinstance(cfg, dict) else None
        display_name = cfg.get("display_name") if isinstance(cfg, dict) else None
        if not display_name and code_full:
            display_name = code_full.split("#")[1] if "#" in code_full else code_full
        if not display_name:
            display_name = cfg.get("name") if isinstance(cfg, dict) else str(cfg)

        days = cfg.get("days_left", 0) if isinstance(cfg, dict) else 0
        days = self.format_days_left(days)

        gb = cfg.get("gb_left", 0) if isinstance(cfg, dict) else 0

        safe_name = self._sanitize_name(display_name)
        frame_obj_name = f"myconfigs_frame_{safe_name}"

        # Build frame and layouts
        frame = QtWidgets.QFrame(self.ui.myconfigs_mainContainer.parentWidget())
        self.ui.myconfigs_mainContainer.addWidget(frame)
        frame.setObjectName(frame_obj_name)
        frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        frame.setMinimumHeight(150)
        frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)

        root_layout = QtWidgets.QVBoxLayout(frame)
        root_layout.setSpacing(8)

        servername_container = QtWidgets.QHBoxLayout()
        servername_container.setSpacing(4)

        lbl_servername = QtWidgets.QLabel(frame)
        lbl_servername.setObjectName(f"myconfigs_frame_{safe_name}_servername")
        lbl_servername.setText(f"Server: {cfg.get("server", "")}")
        lbl_servername.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        servername_container.addWidget(lbl_servername)

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
            lbl_servername.setFont(cons_font)
        except Exception:
            pass

        label_container.addWidget(lbl_name)
        label_container.addWidget(lbl_days)
        label_container.addWidget(lbl_gb)

        # Buttons container
        button_container = QtWidgets.QHBoxLayout()
        button_container.setSpacing(6)

        connect_btn = QtWidgets.QPushButton(frame)
        connect_btn.setObjectName(f"myconfigs_frame_{safe_name}_connectBtn")
        connect_btn.setText("Connect")
        connect_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        share_btn = QtWidgets.QPushButton(frame)
        share_btn.setObjectName(f"myconfigs_frame_{safe_name}_shareBtn")
        share_btn.setText("Share")
        share_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        # Use display_name and config_codes map; handle missing map gracefully
        connect_btn.clicked.connect(
            lambda _checked, dname=display_name, code=config_codes.get(display_name): self._connect_myconfig(dname, code)
        )

        share_btn.clicked.connect(
            lambda _checked, dname=display_name, code=config_codes.get(display_name): self.share_myconfig(dname, code)
        )

        button_container.addWidget(connect_btn)
        button_container.addWidget(share_btn)

        root_layout.addLayout(servername_container)
        root_layout.addLayout(label_container)
        root_layout.addLayout(button_container)

        connect_id = connect_btn.objectName()
        share_id = share_btn.objectName()

        style = f"""
            QFrame {{
                background-color: #0f172a;
                border-radius: 12px;
                border: 1px solid rgba(94, 234, 212, 0.6);
                min-height:185px;
                color:white;
            }}

            QFrame:hover{{
                background-color: rgb(21, 34, 58);
                border: 1px solid rgba(59,130,246,220);
            }}

            QLabel{{
                min-height:65px;
                max-height:65px;
                color:white;
            }}

            QLabel#myconfigs_frame_{safe_name}_servername{{
                min-height:40px;
                max-height:40px;
                color:#38bdf8;
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
                color: white;
            }}
            QPushButton#{share_id} {{
                background-color: #3b82f6;
                color: #f8fafc;
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: bold;
                border: 2px solid #2563eb;
                border-bottom: 4px solid #1d4ed8;
                outline: none;
                min-width: 90px;
                max-height: 20px;
            }}
            QPushButton#{share_id}:hover {{
                background-color: #60a5fa;
                color: white;
            }}
            QPushButton#{share_id}:pressed {{
                background-color: #2563eb;
                border: 2px solid #1d4ed8;
                border-top: 4px solid #1d4ed8;
                padding-top: 12px;
                padding-bottom: 8px;
                color: white;
            }}
        """
        try:
            frame.setStyleSheet(style)
        except Exception:
            pass

        self.ui.myconfigs_mainContainer.addWidget(frame)

    def populate_buy_plans(self, data: dict):
        """Fill buy-config cards from server response data."""
        try:
            plans = data.get('plans', [])
        except Exception:
            plans = []

        frame_stylesheet = """
            QFrame {
                border: 1px solid rgba(17,186,189,140); 
                border-radius: 12px;
                padding: 0px;
                color:white;
            }
            QFrame:hover {
                border: 1px solid rgba(17,186,189,225); 
            }
            QLabel { 
                border: 1px solid rgba(17, 186, 189, 140);
                border-radius: 8px;
                font-weight: 600; font-size: 13px; 
            }
            QLabel:hover { 
                border: 1px solid rgba(17, 186, 189, 255);
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

        for idx, plan in enumerate(plans):
            plan_id = plan.get("id", idx)
            plan_name = plan.get("plan_name", "Unknown Plan")
            plan_servers = plan.get("servers", "")
            plan_usage = plan.get("usage", "")
            plan_time = plan.get("time", "")
            plan_price = plan.get("price", "")
            number_of_users = plan.get("number_of_users", "")

            frame = QtWidgets.QFrame(self.ui.scrollAreaWidgetContents)
            frame.setObjectName(f"buy_frame_{plan_id}")
            frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
            frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
            frame.setMinimumHeight(265)
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

            servers_lbl = QtWidgets.QLabel(frame)
            servers_lbl.setObjectName(f"plan_servers_lbl_{plan_id}")

            servers_list = [str(s) for s in plan_servers]
            max_show = 4
            if len(servers_list) > max_show:
                visible = servers_list[:max_show]
                remaining = len(servers_list) - max_show
                servers_text = ", ".join(visible) + f" and {remaining} more..."
            else:
                servers_text = ", ".join(servers_list)

            servers_lbl.setText(f"Servers : {servers_text}")
            servers_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            price_lbl = QtWidgets.QLabel(frame)
            price_lbl.setObjectName(f"plan_price_lbl_{plan_id}")
            price_lbl.setText(f"Price : {plan_price}")
            price_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            usage_lbl = QtWidgets.QLabel(frame)
            usage_lbl.setObjectName(f"plan_usage_lbl_{plan_id}")
            usage_lbl.setText(f"Usage Limit : {plan_usage}GB")
            usage_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            time_lbl = QtWidgets.QLabel(frame)
            time_lbl.setObjectName(f"plan_time_lbl_{plan_id}")
            time_lbl.setText(f"Time : {plan_time} month")
            time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            usersnum_lbl = QtWidgets.QLabel(frame)
            usersnum_lbl.setObjectName(f"plan_usersnum_lbl_{plan_id}")
            usersnum_lbl.setText(f"User Limit : {number_of_users}")
            usersnum_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            buy_btn = QtWidgets.QPushButton(frame)
            buy_btn.setObjectName(f"buy_btn_{plan_id}")
            buy_btn.setText("Buy")
            buy_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            buy_btn.clicked.connect(lambda _checked, p=plan: self.on_buyconfig_clicked(p))

            # Add widgets to layout
            vbox.addWidget(name_lbl)
            vbox.addWidget(servers_lbl)
            vbox.addWidget(price_lbl)
            vbox.addWidget(usage_lbl)
            vbox.addWidget(time_lbl)
            vbox.addWidget(usersnum_lbl)
            vbox.addWidget(buy_btn)

            self.ui.verticalLayout.addWidget(frame)

    # -------------------- actions and handlers --------------------

    def toggle_visibility(self):
        """Show or hide the main window via tray icon."""
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
        """Handle tray icon activation (clicks)."""
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
        """Prevent closing unless explicitly allowed (use tray/hide instead)."""
        if getattr(self, "_allow_close", False):
            event.accept()
            return
        event.ignore()
        self.hide()

    def force_close(self):
        """Force full application exit (used for final exit)."""
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
        """Show and activate tray icon."""
        try:
            self._allow_close = False
            self.tray_icon.setVisible(True)
            self.tray_icon.show()
            self.tray_enabled = True
            QtWidgets.QApplication.setQuitOnLastWindowClosed(False)
        except Exception:
            pass

    def disable_tray(self):
        """Hide the tray icon."""
        try:
            self.tray_icon.hide()
            self.tray_icon.setVisible(False)
            self.tray_enabled = False
        except Exception:
            pass

    def close_for_logout(self):
        """Close the window when logging out."""
        try:
            self.disable_tray()
            self._allow_close = True
            self.close()
        except Exception:
            pass

    def exit_app(self):
        """Exit the application completely (tray menu -> Exit)."""
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

    def settings_exclusive_proxy_apply_clicked(self):
        """Apply the proxy exception addresses from the text edit."""
        addresses = self.ui.settingsProxyExclusivesTextEdit.toPlainText().split("\n")
        manage_db.set_exclusive_addresses(addresses)
        addresses = manage_db.get_exclusive_addresses()
        if addresses is not None:
            set_proxy_exceptions(addresses)
            return self._show_toast("Exclusive addresses applied successfully",toast_type="info")
        return self._show_toast("There is no address to set as exclusive", 3000, "warning")

    def on_buyconfig_clicked(self, plan: dict):
        """Handle clicking Buy on a plan: confirm and process purchase."""
        try:
            plan_id = plan.get("id", plan.get("plan_id", "Unknown"))
            name = plan.get("plan_name", plan.get("name", "Unknown"))
            usage = plan.get("plan_usage", plan.get("usage", "N/A"))
            time_days = plan.get("plan_time", plan.get("time", "N/A"))
            price = plan.get("plan_price", plan.get("price", "N/A"))
            number_of_users = plan.get("number_of_users", "")
            servers = plan.get("servers","")
            
            servers_list = [str(s) for s in servers]   
            max_show = 3
            if len(servers_list) > max_show:
                visible = servers_list[:max_show]
                remaining = len(servers_list) - max_show
                servers_text = ", ".join(visible) + f" and {remaining} more..."
            else:
                servers_text = ", ".join(servers_list)

            lines = [
                f"📦  Name : {name}",
                f"🌐  Servers : {servers_text}",
                f"📊  Usage : {usage} GB",
                f"⏳  Time : {time_days} month",
                f"💰  Price : {price} coins",
            ]
            if number_of_users not in (None, "", "N/A"):
                lines.append(f"👥  Users : {number_of_users}")

            body = "\n".join(lines) + "\n\nAre you sure you want to buy this plan?"

            resp = ThemedMessageBox.show_message(
                "Confirm Purchase",
                "Do you really want to buy this plan?"
            )

            #if resp == QtWidgets.QMessageBox.StandardButton.Yes:
            if resp == ThemedMessageBox.yes:
                purchase_ok, purchase_result = api_calls.buy_plan(plan_id)
                if purchase_ok:
                    details = purchase_result.get('details', {})
                    configs = details.get('configs', [])
                    for config_obj in configs:

                        code_full = config_obj.get("config_code", "")
                        server = config_obj.get("server", "")
                        display_name = code_full.split("#")[1] if "#" in code_full else code_full
                        gb = details.get("usage") or 0
                        days = (details.get("time") * 30) if details.get("time") is not None else 0

                        config_codes[display_name] = code_full
                        days = self.format_days_left(days)

                        # Add item to combobox
                        self.ui.selectConfigComboBox.addItem(f"{display_name} ({server})")
                        i = self.ui.selectConfigComboBox.count() - 1
                        self.ui.selectConfigComboBox.setItemData(i, {"gb": gb, "days": days}, Qt.ItemDataRole.UserRole)

                        new_config = {
                            "config_code": code_full,
                            "server": server,
                            "display_name": display_name,
                            "days_left": days,
                            "gb_left": gb
                        }
                        self.load_myconfigs([new_config])
                        
                    # Update coins and counts
                    try:
                        new_coin_count = int(self.ui.coinNumber.text()) - details.get("price", 0)
                        self.ui.coinNumber.setText(str(new_coin_count))
                        self.ui.accountCoinsCount.setText(str(new_coin_count))
                        self.ui.accountAllConfigsCount.setText(str(int(self.ui.accountAllConfigsCount.text()) + int(len(configs))))
                    except Exception:
                        pass

                    return self._show_toast("Plan Successfully purchased ✅",toast_type="success")
                return self._show_toast(purchase_result, 3000, "alert")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Error in on_buyconfig_clicked:\n{e}")

    def on_buycoin_clicked(self):
        """Open admin Telegram chat for buying coins."""
        url = f"https://t.me/{self.admin_telegram}".replace("@", "")
        webbrowser.open(url, new=2)

    def on_power_clicked(self):
        """Toggle connect/disconnect (power button)."""
        current = self.ui.connectionStatusText.text()
        selected = self.ui.selectConfigComboBox.currentText()

        if current in ("Not Connected", "Disconnected") and selected != "":

            self.power_button_fancy.set_state("connecting")
            self.power_button_fancy.setDisabled(True)

            self.ui.connectionStatusText.setText("Connecting...")
            self.ui.selectConfigComboBox.setDisabled(True)

            QtCore.QTimer.singleShot(2000, self._on_connected)

            # config_codes may be empty — use get
            cfg_code = config_codes.get(selected.split(" ")[0])
            try:
                self.xray_client = XrayClient(cfg_code, set_system_proxy=True)
                self.xray_client.start()
            except Exception:
                pass
        else:
            # Disconnect
            self.power_button_fancy.set_state("disconnected")
            self.ui.connectionStatusText.setText("Disconnected")

            self.power_button_fancy.setDisabled(False)
            self.ui.selectConfigComboBox.setDisabled(False)

            if selected != "":
                try:
                    self.xray_client.stop()
                except Exception:
                    pass

    def _on_connected(self):
        """UI update after connection established."""
        self.power_button_fancy.set_state("connected")
        self.power_button_fancy.setDisabled(False)
        self.ui.connectionStatusText.setText("Connected")
        self.ui.selectConfigComboBox.setDisabled(True)

    def on_menu_clicked(self):
        """Animate opening/closing of side menu."""
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

        # Keep references to avoid garbage collection
        menu_btn._anim = anim_menu
        side_menu._anim = anim_side

        self.menu_toggle = not self.menu_toggle

    def on_logout_clicked(self):
        """Start logout sequence in a background thread."""
        try:
            self.ui.accountlogoutButton.setDisabled(True)
        except Exception:
            pass

        try:
            self._show_toast("Logging out...", 1200, "info")
        except Exception:
            pass

        t = threading.Thread(target=self._perform_logout, daemon=True)
        t.start()

    def _perform_logout(self):
        """Actual logout operations: stop xray, clear DB auth, clear config_codes, emit finished signal."""
        ok = True
        msg = "Logged out"
        try:
            # Attempt to stop xray client
            try:
                if hasattr(self, "xray_client") and self.xray_client is not None:
                    try:
                        self.xray_client.stop()
                    except Exception:
                        pass
            except Exception:
                pass

            # Clear Auth table in local DB
            try:
                if 'manage_db' in globals() and manage_db is not None:
                    try:
                        manage_db.execute_database("DELETE FROM Auth;")
                    except Exception:
                        # fallback: direct sqlite connection
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

            # Clear config_codes
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

    def _handle_logout_finished(self, ok: bool, msg: str):
        """Handle end of logout: show message and switch windows if successful."""
        try:
            self.ui.accountlogoutButton.setDisabled(False)
        except Exception:
            pass

        try:
            self._show_toast(msg, 2000, "info" if ok else "alert")
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

    def _connect_myconfig(self, display_name: str, config_code: str):
        """Connect to a config from the my-configs page (equivalent of Connect button)."""
        try:
            if not config_code:
                return self._show_toast("No config code available", 1800, "info")

            current = self.ui.connectionStatusText.text()
            if current in ("Not Connected", "Disconnected"):
                # Same connect logic as on_power_clicked
                self.power_button_fancy.set_state("connecting")
                self.power_button_fancy.setDisabled(True)
                self.ui.connectionStatusText.setText("Connecting...")
                self.ui.selectConfigComboBox.setDisabled(True)

                index = self.ui.selectConfigComboBox.findText(display_name, QtCore.Qt.MatchFlag.MatchContains)
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
                return self._show_toast("You already connected. Please disconnect first.", toast_type="info")
        except Exception as e:
            try:
                self._show_toast(f"Connect error: {e}", 2000, "error")
            except Exception:
                pass

    def share_myconfig(self, display_name:str, config_code: str):
        dlg = ShareConfigDialog(link=config_code, display_name=display_name, parent=self)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.exec()

    def _sanitize_name(self, name: str) -> str:
        """Convert a name to a safe string suitable for object naming."""
        import re
        if not name:
            return "unnamed"
        s = re.sub(r"[^0-9a-zA-Z]+", "_", str(name))
        return s.strip("_") or "unnamed"

    def _show_toast(self, text: str, duration: int = 2500, toast_type: str = "info"):
        """Show a temporary popup toast message."""
        toast = PopupToast(self, text=text, duration=duration, toast_type=toast_type)
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
            self._show_toast(msg, toast_type="warning")
            return

        username = self.ui.usernameLineEdit.text().strip()
        password = self.ui.passwordLineEdit.text()
        login_window.ui.loginButton.setDisabled(True)
        ok , msg = api_calls.login(username=username,password=password)
        if ok:
            try:
                main_window._refresh_userdata()
            except:
                pass
            main_window.show()
            main_window.enable_tray() 
            login_window.ui.loginButton.setDisabled(False)
            login_window._programmatic_close = True
            return login_window.close()
        login_window.ui.loginButton.setDisabled(False)
        return self._show_toast(msg, duration=1800, toast_type="alert")

    def on_submit_clicked(self):
        ok, msg = self.validate_submit()
        if not ok:
            self._show_toast(msg, toast_type="warning")
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
        return self._show_toast(msg, duration=1800, toast_type="alert")

    def _show_toast(self, text: str, duration: int = 2500, toast_type: str = "info"):
        """Show a temporary popup toast message."""
        toast = PopupToast(self, text=text, duration=duration, toast_type=toast_type)
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
                        main_window._refresh_userdata()
                    except:
                        pass
                    main_window.show()
                    main_window.enable_tray() 
                    self.ui.verifyButton.setDisabled(False)
                    email_verify_window._programmatic_close = True
                    return email_verify_window.close()
                self.ui.verifyButton.setDisabled(False)
                return self._show_toast(msg,2000,"alert")
            self.ui.verifyButton.setDisabled(False)
            return self._show_toast(msg,2000,"alert")
        return self._show_toast(msg, 2000, "warning")

    def on_back_to_login_clicked(self):
        login_window.show()
        return email_verify_window.close()

    def on_resend_code_clicked(self):
        self.ui.resendCodeButton.setDisabled(True)
        ok ,msg = api_calls.resend_verification_code(self.email)
        if ok:
            self._show_toast(msg, 2000, "info")
            return self.ui.resendCodeButton.setDisabled(False)
        self._show_toast(msg, 2000, "alert")
        return self.ui.resendCodeButton.setDisabled(False)

    def set_data(self,email,username,password):
        self.email = email
        self.username = username
        self.password = password

    def _show_toast(self, text: str, duration: int = 2500, toast_type: str = "info"):
        """Show a temporary popup toast message."""
        toast = PopupToast(self, text=text, duration=duration, toast_type=toast_type)
        toast.show_toast()

if __name__ == "__main__":
    
    manage_db = ManageDatabase()
    manage_db.init_db()

    backaddr_full = manage_db.get_backaddr()
    if CONFIG['MODE']=="IP":
        backaddr_full = f"http://{backaddr_full['ip']}:{backaddr_full['port']}"
    elif CONFIG['MODE']=="DOMAIN":
        backaddr_full = f"http://{backaddr_full['sub']}.{backaddr_full['name']}.{backaddr_full['tld']}:{backaddr_full['port']}"
    else:
        backaddr_full = f"http://{backaddr_full['ip']}:{backaddr_full['port']}"

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
