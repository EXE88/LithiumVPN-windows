from PyQt6 import QtWidgets, QtGui, QtCore

class RoundedLine(QtWidgets.QWidget):
    def __init__(self, parent=None, x: float = 10.0, y: float = 70.0,
                 length: float = 71.0, thickness: float = 2.0,
                 color: QtGui.QColor = QtGui.QColor(230, 230, 230),
                 vertical: bool = True):
        super().__init__(parent)
        self._x = float(x)
        self._y = float(y)
        self._length = float(length)
        self._thickness = float(thickness)
        self._color = color
        self._vertical = bool(vertical)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._update_geometry()

    def _update_geometry(self):
        pad = int(max(2, round(self._thickness / 2.0 + 2)))
        if self._vertical:
            w = int(max(1, round(self._thickness))) + pad * 2
            h = int(max(1, round(self._length))) + pad * 2
            ix = int(round(self._x)) - (w // 2)
            iy = int(round(self._y)) - pad
        else:
            w = int(max(1, round(self._length))) + pad * 2
            h = int(max(1, round(self._thickness))) + pad * 2
            ix = int(round(self._x)) - pad
            iy = int(round(self._y)) - (h // 2)

        self.setGeometry(ix, iy, w, h)
        self.update()

    def set_position(self, x: float, y: float):
        self._x = float(x); self._y = float(y)
        self._update_geometry()

    def set_length(self, length: float):
        self._length = float(length)
        self._update_geometry()

    def set_thickness(self, thickness: float):
        self._thickness = float(thickness)
        self._update_geometry()

    def set_color(self, color: QtGui.QColor):
        self._color = color
        self.update()

    def set_vertical(self, vertical: bool):
        self._vertical = bool(vertical)
        self._update_geometry()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pen = QtGui.QPen(self._color)
        pen.setWidthF(self._thickness)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        if self._vertical:
            cx = float(self.width()) / 2.0
            start_y = (self.height() - self._length) / 2.0
            start = QtCore.QPointF(cx, start_y)
            end = QtCore.QPointF(cx, start_y + self._length)
        else:
            cy = float(self.height()) / 2.0
            start_x = (self.width() - self._length) / 2.0
            start = QtCore.QPointF(start_x, cy)
            end = QtCore.QPointF(start_x + self._length, cy)

        p.drawLine(start, end)
        p.end()
