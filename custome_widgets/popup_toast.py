from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation

class PopupToast(QtWidgets.QWidget):
    def __init__(self, parent, text: str, duration=2500, toast_type="info"):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.duration = duration

        #color styles
        toast_colors = {
            "info": {"bg": "rgba(50, 115, 220, 220)", "border": "#2B70E0", "text": "white"},
            "success": {"bg": "rgba(76, 175, 80, 220)", "border": "#4CAF50", "text": "white"},
            "warning": {"bg": "rgba(255, 193, 7, 220)", "border": "#FFC107", "text": "black"},
            "error": {"bg": "rgba(244, 67, 54, 220)", "border": "#F44336", "text": "white"},
            "alert": {"bg": "rgba(255, 87, 34, 220)", "border": "#FF5722", "text": "white"},
        }

        style = toast_colors.get(toast_type.lower(), toast_colors["info"])

        # Container
        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("toast_container")
        self.container.setStyleSheet(f"""
            QFrame#toast_container {{
                background-color: {style['bg']};
                color: {style['text']};
                border-radius: 12px;
                padding: 12px 20px;
                font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
                font-size: 14px;
                border: 1px solid {style['border']};
            }}
            QLabel {{
                background-color: transparent;
                color: {style['text']};
                font-weight: 500;
            }}
        """)

        # Label
        self.label = QtWidgets.QLabel(text, parent=self.container)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(f"background-color: transparent; color: {style['text']};")
        self.label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QtWidgets.QHBoxLayout(self.container)
        layout.addWidget(self.label)
        layout.setContentsMargins(8,6,8,6)
        self.container.setLayout(layout)

        # effects and animations
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

        min_width = 120
        max_width = min(400, pw - 40)

        self.label.setWordWrap(False)
        self.label.adjustSize()
        text_width = self.label.sizeHint().width() + 57
        content_width = min(max_width, max(min_width, text_width))

        if text_width > max_width:
            self.label.setWordWrap(True)
            content_width = max_width

        self.container.setFixedWidth(content_width)
        self.container.adjustSize()

        extra_height = 6
        tw = self.container.width()
        th = self.container.height() + extra_height
        self.resize(tw, th)

        start_x = pw + 20
        end_x = (pw - tw) // 2
        y = 20
        self.move(start_x, y)
        self.show()
        self.raise_()

        # Fade in
        self.opacity_effect.setOpacity(0.0)
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(250)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

        # Slide in (smooth)
        self.slide_anim.stop()
        self.slide_anim.setDuration(250)
        self.slide_anim.setStartValue(QtCore.QPoint(start_x, y))
        self.slide_anim.setEndValue(QtCore.QPoint(end_x, y))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_anim.start()

        QtCore.QTimer.singleShot(self.duration, self._hide_sequence)


    def _hide_sequence(self):
        parent = self.parent() or self
        pw = parent.width()
        y = self.y()
        end_x = pw + 20 

        # Fade out
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(250)
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.start()

        # Slide out
        self.slide_anim.stop()
        self.slide_anim.setDuration(250)
        self.slide_anim.setStartValue(self.pos())
        self.slide_anim.setEndValue(QtCore.QPoint(end_x, y))
        self.slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.slide_anim.start()
        self.slide_anim.finished.connect(self.hide)