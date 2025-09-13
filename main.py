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
        username = "username"
        self.ui.usernameText.setFixedWidth(len(username)*10)
        self.ui.usernameText.setText(username)
        self.ui.coinNumber.setText("160")
        self.ui.selectConfigComboBox.clear()
        self.ui.selectConfigComboBox.addItems([
            "Iran-06lw1wpj", "Iran-d7r9arzn", "Iran-ye0NdN6j", "Iran-7nmSP6LR"
        ])

        size = QtCore.QSize(150, 150)
        tint = QtGui.QColor(0, 0, 0)
        self.set_svg_icon_on_button(self.ui.powerButton, ':/icons/icons/power.svg', size, tint_color=tint)

    def _connect_signals(self):
        self.ui.powerButton.clicked.connect(self.on_power_clicked)
        self.ui.menuButton.clicked.connect(self.on_menu_clicked)
        self.ui.pushButton.clicked.connect(lambda: self.on_sidebutton_clicked("Home"))
        self.ui.pushButton_2.clicked.connect(lambda: self.on_sidebutton_clicked("Account"))

    def on_power_clicked(self):
        current = self.ui.connectionStatusText.text()
        if current in ("Not Connected", "Disconnected"):
            self.ui.connectionStatusText.setText("Connecting...")
            QtWidgets.QMessageBox.information(self, "Action", f"Connected to {self.ui.selectConfigComboBox.currentText()}")
            self.ui.connectionStatusText.setText("Connected")
        else:
            self.ui.connectionStatusText.setText("Disconnected")

    def on_menu_clicked(self):
        QtWidgets.QMessageBox.information(self, "Menu", "Menu clicked")

    def on_sidebutton_clicked(self, name):
        QtWidgets.QMessageBox.information(self, name, f"{name} clicked")

    def set_svg_icon_on_button(self, button: QtWidgets.QPushButton, resource_path: str, size: QtCore.QSize, tint_color: QtGui.QColor | None = None):
        pix = None

        if SVG_AVAILABLE and resource_path.lower().endswith('.svg'):
            try:
                renderer = QSvgRenderer(resource_path)
                pix = QtGui.QPixmap(size)
                pix.fill(QtCore.Qt.GlobalColor.transparent)
                painter = QtGui.QPainter(pix)
                painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
                renderer.render(painter, QtCore.QRectF(0, 0, size.width(), size.height()))
                painter.end()
            except Exception:
                pix = None

        if pix is None:
            pix = QtGui.QPixmap(resource_path)
            if pix.isNull():
                pix = QtGui.QPixmap(size)
                pix.fill(QtCore.Qt.GlobalColor.transparent)
            else:
                pix = pix.scaled(
                    size,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )

        if tint_color is not None:
            img = pix.toImage().convertToFormat(QtGui.QImage.Format.Format_ARGB32)

            w = img.width()
            h = img.height()

            tr = tint_color.red()
            tg = tint_color.green()
            tb = tint_color.blue()

            for y in range(h):
                for x in range(w):
                    col = img.pixelColor(x, y)
                    a = col.alpha()
                    if a == 0:
                        continue
                    new_col = QtGui.QColor(tr, tg, tb, a)
                    img.setPixelColor(x, y, new_col)

            pix = QtGui.QPixmap.fromImage(img)

        button.setIcon(QtGui.QIcon(pix))
        button.setIconSize(size)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainAppWindow()
    window.show()
    sys.exit(app.exec())
