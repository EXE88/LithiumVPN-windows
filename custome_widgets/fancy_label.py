from PyQt6 import QtCore, QtGui, QtWidgets

class FancyLabel:
    def __init__(self, parent, target_label, text="", font_size=28):
        font = QtGui.QFont()
        font.setFamily("Roboto Mono")
        font.setPointSize(font_size)

        x = target_label.x()
        y = target_label.y()
        w = target_label.width()
        h = target_label.height()

        glow_blur = 40
        shadow_blur = 8
        shadow_offset = (0, 3)
        padding = int(glow_blur)

        big_rect = QtCore.QRect(x - padding, y - padding, w + padding*2, h + padding*2)

        self.glowText = QtWidgets.QLabel(parent=parent)
        self.glowText.setGeometry(big_rect)
        self.glowText.setFont(font)
        self.glowText.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.glowText.setStyleSheet("color: rgba(6, 182, 212, 200);")
        self.glowText.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        glow_effect = QtWidgets.QGraphicsDropShadowEffect(self.glowText)
        glow_effect.setOffset(0, 0)
        glow_effect.setBlurRadius(glow_blur)
        glow_effect.setColor(QtGui.QColor(6, 182, 212, 200))
        self.glowText.setGraphicsEffect(glow_effect)

        self.shadowText = QtWidgets.QLabel(parent=parent)
        self.shadowText.setGeometry(big_rect)
        self.shadowText.setFont(font)
        self.shadowText.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.shadowText.setStyleSheet("color: rgba(0,0,0,0);")
        self.shadowText.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        drop_effect = QtWidgets.QGraphicsDropShadowEffect(self.shadowText)
        drop_effect.setOffset(*shadow_offset)
        drop_effect.setBlurRadius(shadow_blur)
        drop_effect.setColor(QtGui.QColor(0, 0, 0, 160))
        self.shadowText.setGraphicsEffect(drop_effect)

        target_label.deleteLater()
        self.headerText = QtWidgets.QLabel(parent=parent)
        self.headerText.setGeometry(QtCore.QRect(x, y, w, h))
        self.headerText.setFont(font)
        self.headerText.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.headerText.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.headerText.setStyleSheet(
            "color:qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.488636, y2:0, "
            "stop:0 rgba(59, 130, 246, 255), stop:1 rgba(6, 182, 212, 255))"
        )

        self.glowText.stackUnder(self.shadowText)
        self.shadowText.stackUnder(self.headerText)

        self.setText(text)

    def setText(self, text: str):
        self.glowText.setText(text)
        self.shadowText.setText(text)
        self.headerText.setText(text)
