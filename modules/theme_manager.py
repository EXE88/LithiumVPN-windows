import os
from typing import Dict
from PyQt6 import QtGui, QtWidgets, QtCore


class ThemeManager:
    def __init__(self, main_window: QtWidgets.QMainWindow, assets_root: str = "assets/themes"):
        self.main_window = main_window
        self.assets_root = assets_root

    def _load_qss_files(self, theme: str) -> Dict[str, str]:
        path = os.path.join(self.assets_root, theme)
        out = {}
        if not os.path.isdir(path):
            return out
        for fn in os.listdir(path):
            if not fn.lower().endswith('.qss'):
                continue
            full = os.path.join(path, fn)
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    out[fn] = f.read()
            except Exception:
                continue
        return out

    def _apply_qss_map(self, qss_map: Dict[str, str]):
        ui = getattr(self.main_window, 'ui', None)
        if ui is None:
            return

        for name, content in qss_map.items():
            key = name.lower()
            try:
                if 'maintab' in key or 'mainwindow' in key or key.startswith('main'):
                    try:
                        self.main_window.setStyleSheet(content)
                    except Exception:
                        QtWidgets.QApplication.instance().setStyleSheet(content)
                elif 'home' in key:
                    getattr(ui, 'homeTab', ui).setStyleSheet(content)
                elif 'account' in key:
                    getattr(ui, 'accountTab', ui).setStyleSheet(content)
                elif 'buycoin' in key:
                    getattr(ui, 'buycoinTab', ui).setStyleSheet(content)
                elif 'buyconfig_card' in key:
                    pass               
                elif 'buyconfig' in key:
                    getattr(ui, 'buyconfigTab', ui).setStyleSheet(content)
                elif 'settings' in key:
                    getattr(ui, 'settingsTab', ui).setStyleSheet(content)
                elif 'myconfig_card' in key:
                    pass
                elif 'myconfigs' in key:
                    getattr(ui, 'myconfigsTab', ui).setStyleSheet(content)
                elif 'centralwidget' in key:
                    getattr(ui, 'centralwidget', ui).setStyleSheet(content)
                elif 'sidemenu' in key:
                    getattr(ui, 'sideMenu', ui).setStyleSheet(content)                    
                else:
                    try:
                        ui.centralwidget.setStyleSheet(content)
                    except Exception:
                        pass
            except Exception:
                pass

    def _apply_background(self, image_name: str):
        lbl = getattr(self.main_window.ui, 'backgroundImage', None)
        if lbl is None:
            return
        pix = QtGui.QPixmap(f":images/images/{image_name}")
        if pix.isNull():
            return
        try:
            if lbl.size().isEmpty():
                lbl.setPixmap(pix)
                lbl.setScaledContents(True)
            else:
                scaled = pix.scaled(lbl.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding, QtCore.Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(scaled)
                lbl.setScaledContents(False)
        except Exception:
            lbl.setPixmap(pix)
            lbl.setScaledContents(True)

    def apply_theme(self, theme: str):
        qss_map = self._load_qss_files(theme)
        if qss_map:
            self._apply_qss_map(qss_map)

        bg_map = {
            'dark': 'dark_ocean_bg.png',
            'light': 'white_gradiant_bg.jpg',
            'blue': 'blue_gradiant_bg.jpg',
        }
        img = bg_map.get(theme)
        if img:
            self._apply_background(img)

    def apply_dark(self):
        self.apply_theme('dark')

    def apply_light(self):
        self.apply_theme('light')

    def apply_blue(self):
        self.apply_theme('blue')
