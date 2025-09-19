from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation

class PopupToast(QtWidgets.QWidget):
    def __init__(self, parent, text: str, duration=2500):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.duration = duration

        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("toast_container")
        self.container.setStyleSheet("""
            QFrame#toast_container {
                background-color: rgba(40,40,40,230);
                color: white;
                border-radius: 10px;
                padding: 10px 14px;
                font-family: 'SF Pro Display';
                font-size: 13px;
            }
        """)
        label = QtWidgets.QLabel(text, parent=self.container)
        label.setWordWrap(False)
        label.setStyleSheet("background-color: transparent; color: white;")
        label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QtWidgets.QHBoxLayout(self.container)
        layout.addWidget(label)
        layout.setContentsMargins(8,6,8,6)
        self.container.setLayout(layout)

        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.opacity_anim.setDuration(300)
        self.slide_anim = QPropertyAnimation(self, b"pos", self)
        self.slide_anim.setDuration(300)
        self.hide()

    def show_toast(self):
        parent = self.parent() or self
        pw = parent.width()
        tw = min(300, pw - 40)
        th = self.container.sizeHint().height()
        self.resize(tw, th)
        start_x = pw
        end_x = pw - tw - 20
        y = 20
        self.move(start_x, y)
        self.show()
        self.raise_()

        self.opacity_effect.setOpacity(0.0)
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

        self.slide_anim.stop()
        self.slide_anim.setStartValue(QtCore.QPoint(start_x, y))
        self.slide_anim.setEndValue(QtCore.QPoint(end_x, y))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_anim.start()

        QtCore.QTimer.singleShot(self.duration, self._hide_sequence)

    def _hide_sequence(self):
        parent = self.parent() or self
        pw = parent.width()
        y = self.y()
        end_x = pw
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.start()

        self.slide_anim.stop()
        self.slide_anim.setStartValue(self.pos())
        self.slide_anim.setEndValue(QtCore.QPoint(end_x, y))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.slide_anim.start()
        self.slide_anim.finished.connect(self.hide)
