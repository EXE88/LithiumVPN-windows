from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor

class RGBLabel(QLabel):
    def __init__(self, parent=None, target_label=None, text="", update_interval=50):
        super().__init__(parent)
        
        self.target_label = target_label
        if self.target_label:
            self.target_label.hide()
            self.setText(text or self.target_label.text())
            self.setGeometry(self.target_label.geometry())
            self.setAlignment(self.target_label.alignment())
            self.setFont(self.target_label.font())
            self.setMinimumSize(self.target_label.minimumSize())
            self.setMaximumSize(self.target_label.maximumSize())
            self.setSizePolicy(self.target_label.sizePolicy())
        
        self.hue = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_color)
        self.timer.start(update_interval)
        
    def _update_color(self):
        self.hue = (self.hue + 2) % 360
        color = QColor.fromHsv(self.hue, 255, 255)
        original_style = self.target_label.styleSheet() if self.target_label else ""
        style = f"""
            QLabel {{
                color: rgb({color.red()}, {color.green()}, {color.blue()});
                background-color:transparent;
                {original_style.replace('QLabel {', '').replace('}', '').replace('color:', '/*color:*/') if original_style else ''}
            }}
        """
        self.setStyleSheet(style)
    
    def setText(self, text):
        super().setText(text)
        if self.target_label:
            self.target_label.setText(text)