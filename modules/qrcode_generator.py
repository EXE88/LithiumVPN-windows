import io
from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QDialog, QMessageBox
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt
import qrcode
from custome_widgets.popup_toast import PopupToast

class ShareConfigDialog(QDialog):
    def __init__(self, link: str, display_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Share Config {display_name}")
        self.setMinimumSize(360, 450)
        self.link = link

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.link_edit = QLineEdit()
        self.link_edit.setMinimumHeight(40)
        self.link_edit.setFont(QFont("Consolas", 11))
        self.link_edit.setText(self.link)
        self.link_edit.setReadOnly(True)
        self.link_edit.setCursorPosition(0)
        layout.addWidget(self.link_edit)

        self.qr_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setFixedSize(300, 300)
        self.qr_label.setStyleSheet("background: white; border: 1px solid #ccc;")
        layout.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        btns = QHBoxLayout()

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("copyBtn")
        copy_btn.clicked.connect(self.copy_link)
        btns.addWidget(copy_btn)

        layout.addLayout(btns)
        self.setLayout(layout)

        self.setStyleSheet("""
            QPushButton#copyBtn {
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
            }
            QPushButton#copyBtn:hover {
                background-color: #60a5fa;
                color: white;
            }
            QPushButton#copyBtn:pressed {
                background-color: #2563eb;
                border: 2px solid #1d4ed8;
                border-top: 4px solid #1d4ed8;
                padding-top: 12px;
                padding-bottom: 8px;
            }
        """)

        try:
            self._generate_and_show_qr(self.link)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in generating Qrcode : {e}")

    def _generate_and_show_qr(self, text: str):
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        png_data = buffer.getvalue()

        pix = QPixmap()
        pix.loadFromData(png_data)
        scaled = pix.scaled(self.qr_label.width(), self.qr_label.height(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        self.qr_label.setPixmap(scaled)

    def copy_link(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.link_edit.text())
        self._show_toast("Config code copied in your clipboard successfully.", toast_type="info")

    def _show_toast(self, text: str, duration: int = 2500, toast_type: str = "info"):
        """Show a temporary popup toast message."""
        toast = PopupToast(self, text=text, duration=duration, toast_type=toast_type)
        toast.show_toast()