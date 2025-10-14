from typing import Optional, Tuple, Union
from PyQt6 import QtCore, QtGui, QtWidgets

ColorLike = Union[QtGui.QColor, Tuple[int, int, int], Tuple[int, int, int, int], str]

def to_qcolor(c: ColorLike) -> QtGui.QColor:
    if isinstance(c, QtGui.QColor):
        return c
    if isinstance(c, tuple):
        if len(c) == 3:
            r, g, b = c
            a = 255
        elif len(c) == 4:
            r, g, b, a = c
        else:
            raise ValueError("tuple color must be (r,g,b) or (r,g,b,a)")
        return QtGui.QColor(r, g, b, a)
    if isinstance(c, str):
        qc = QtGui.QColor(c)
        if not qc.isValid():
            raise ValueError(f"invalid color string: {c}")
        return qc
    raise TypeError("unsupported color type")

def qcolor_to_rgba_str(qc: QtGui.QColor) -> str:
    return f"rgba({qc.red()}, {qc.green()}, {qc.blue()}, {qc.alpha()})"

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

class FancyLabelBetter:
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        target_label: QtWidgets.QLabel,
        text: str = "",
        font_name: Optional[str] = None,
        font_size: Optional[int] = None,
        glow_color: ColorLike = (6, 182, 212, 200),
        header_color_stop0: ColorLike = (59, 130, 246, 255),
        header_color_stop1: ColorLike = (6, 182, 212, 255),
        shadow_color: ColorLike = (0, 0, 0, 160),
        glow_blur: int = 40,
        shadow_blur: int = 8,
        shadow_offset: Tuple[int, int] = (0, 3),
    ):
        target_font: QtGui.QFont = target_label.font()
        target_alignment = target_label.alignment()
        target_sizepolicy = target_label.sizePolicy()
        target_wordwrap = target_label.wordWrap()
        target_stylesheet = target_label.styleSheet()

        x = target_label.x()
        y = target_label.y()
        w = target_label.width()
        h = target_label.height()

        use_family = font_name if font_name is not None else target_font.family()
        t_point_size = target_font.pointSize()
        use_point_size = font_size if font_size is not None else (t_point_size if t_point_size > 0 else 28)

        font = QtGui.QFont()
        font.setFamily(use_family)
        font.setPointSize(use_point_size)

        padding = int(glow_blur)
        big_rect = QtCore.QRect(x - padding, y - padding, w + padding * 2, h + padding * 2)

        qc_glow = to_qcolor(glow_color)
        qc_shadow = to_qcolor(shadow_color)
        qc_h0 = to_qcolor(header_color_stop0)
        qc_h1 = to_qcolor(header_color_stop1)

        def _init_label(lbl: QtWidgets.QLabel, geom: QtCore.QRect):
            lbl.setGeometry(geom)
            lbl.setFont(font)
            lbl.setAlignment(target_alignment)
            lbl.setWordWrap(target_wordwrap)
            lbl.setSizePolicy(target_sizepolicy)
            lbl.setContentsMargins(0, 0, 0, 0)
            try:
                lbl.setIndent(0)
            except Exception:
                pass
            lbl.setTextFormat(QtCore.Qt.TextFormat.PlainText)
            lbl.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.glowText = QtWidgets.QLabel(parent=parent)
        _init_label(self.glowText, big_rect)
        self.glowText.setStyleSheet(f"color: {qcolor_to_rgba_str(qc_glow)};")
        glow_effect = QtWidgets.QGraphicsDropShadowEffect(self.glowText)
        glow_effect.setOffset(0, 0)
        glow_effect.setBlurRadius(glow_blur)
        glow_effect.setColor(qc_glow)
        self.glowText.setGraphicsEffect(glow_effect)

        self.shadowText = QtWidgets.QLabel(parent=parent)
        _init_label(self.shadowText, big_rect)
        self.shadowText.setStyleSheet("color: rgba(0,0,0,0);")
        drop_effect = QtWidgets.QGraphicsDropShadowEffect(self.shadowText)
        drop_effect.setOffset(*shadow_offset)
        drop_effect.setBlurRadius(shadow_blur)
        drop_effect.setColor(qc_shadow)
        self.shadowText.setGraphicsEffect(drop_effect)

        target_label.deleteLater()

        self.headerText = QtWidgets.QLabel(parent=parent)
        _init_label(self.headerText, big_rect)

        if target_stylesheet:
            try:
                self.headerText.setStyleSheet(target_stylesheet)
            except Exception:
                pass
        else:
            grad_css = (
                "color:qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.488636, y2:0, "
                f"stop:0 {qcolor_to_rgba_str(qc_h0)}, stop:1 {qcolor_to_rgba_str(qc_h1)})"
            )
            self.headerText.setStyleSheet(grad_css)

        if target_sizepolicy.horizontalPolicy() == QtWidgets.QSizePolicy.Policy.Fixed:
            self.headerText.setFixedWidth(w)
            self.glowText.setFixedWidth(w + padding*2)
            self.shadowText.setFixedWidth(w + padding*2)

        self.glowText.stackUnder(self.shadowText)
        self.shadowText.stackUnder(self.headerText)

        self.setText(text)

    def setText(self, text: str):
        self.glowText.setText(text)
        self.shadowText.setText(text)
        self.headerText.setText(text)
