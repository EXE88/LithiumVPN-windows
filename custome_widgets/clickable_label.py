from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal

class ClickableLabel(QtWidgets.QLabel):
    clicked = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)