from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QEventLoop
from PyQt6.QtGui import QFont


class ThemedMessageBox(QWidget):
    response = pyqtSignal(str)
    yes = "yes"
    no = "no"

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 180)

        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        container = QWidget(self)
        container.setGeometry(0, 0, 420, 180)
        container.setObjectName("container")
        container.setStyleSheet("""
            QWidget#container {
                background: qlineargradient(
                    spread:pad,
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(23, 35, 61, 255),
                    stop:1 rgba(40, 60, 102, 255)
                );
                border-radius: 15px;
                border: 2px solid rgba(59, 130, 246, 90);
            }
            QLabel#titleLabel {
                color: qlineargradient(
                    spread:pad,
                    x1:0.5, y1:1, x2:0.488636, y2:0,
                    stop:0 rgba(59, 130, 246, 255),
                    stop:1 rgba(6, 182, 212, 255)
                );
                font-size: 16pt;
                font-weight: bold;
            }
            QLabel#messageLabel {
                color: white;
                font-size: 13pt;
                font-weight: bold;
            }
            QPushButton {
                background-color: rgb(59, 130, 246);
                color: white;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: rgb(6, 182, 212);
            }
            QPushButton:pressed {
                background-color: rgb(3, 142, 170);
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        message_label = QLabel(message)
        message_label.setObjectName("messageLabel")
        message_label.setWordWrap(False)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        yes_button = QPushButton("Yes")
        yes_button.clicked.connect(lambda: self.emit_response("yes"))
        button_layout.addWidget(yes_button)

        no_button = QPushButton("No")
        no_button.clicked.connect(lambda: self.emit_response("no"))
        button_layout.addWidget(no_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(220)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.setWindowOpacity(0.0)
        self.animation.start()
        self._response_value = None

    def emit_response(self, value: str):
        self._response_value = value
        self.response.emit(value)

    @staticmethod
    def show_message(title: str, message: str, parent=None) -> str:
        dialog = ThemedMessageBox(title, message, parent)
        loop = QEventLoop()
        dialog.response.connect(lambda *_: loop.quit())
        dialog.show()
        loop.exec()
        result = dialog._response_value
        dialog.close()
        return result