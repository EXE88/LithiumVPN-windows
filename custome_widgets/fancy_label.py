from typing import Optional, Tuple, Union
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsDropShadowEffect

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


class GlowText:
    def __init__(
        self,
        text: str,
        font_name="Arial",
        font_size=50,
        bold=True,
        text_color=QColor("white"),
        glow_color=QColor(255, 255, 0),
        blur=80,
        alpha=255,
    ):
        self.item = QGraphicsTextItem(text)

        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        self.font = QFont(font_name, font_size, weight)
        self.item.setFont(self.font)
        self.item.setDefaultTextColor(text_color)

        self.glow = QGraphicsDropShadowEffect()
        self.glow.setOffset(0, 0)
        self.glow.setBlurRadius(blur)

        self.glow_color = QColor(glow_color)
        self.glow_color.setAlpha(alpha)
        self.glow.setColor(self.glow_color)

        self.item.setGraphicsEffect(self.glow)

    # ---------- factory ----------
    @classmethod
    def from_label(
        cls,
        parent: QtWidgets.QWidget,
        target_label: QtWidgets.QLabel,
        text: str,
        font_name: str = "Arial",
        glow_color=QColor(255, 255, 0),
        blur: int = 50,
        alpha: int = 255,
        y_offset: int = 10,
        bold: bool = True,
    ):
        scene = QtWidgets.QGraphicsScene(parent)
        view = QtWidgets.QGraphicsView(scene, parent)

        view.setGeometry(
            QRect(
                target_label.x()-30,
                target_label.y()-30 + y_offset,
                target_label.width()+60,
                target_label.height()+60,
            )
        )

        view.setStyleSheet("background: transparent;")
        view.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        glow_text = cls(
            text=text,
            font_name=font_name,
            font_size=target_label.font().pointSize(),
            bold=bold,
            text_color=QColor(255, 255, 255),
            glow_color=glow_color,
            blur=blur,
            alpha=alpha,
        )

        scene.addItem(glow_text.item)
        target_label.deleteLater()

        glow_text.scene = scene
        glow_text.view = view

        return glow_text

    # ---------- setters ----------
    def set_text(self, text):
        self.item.setPlainText(text)

    def set_position(self, x, y):
        self.item.setPos(x, y)

    def set_font(self, name=None, size=None, bold=None):
        if name:
            self.font.setFamily(name)
        if size:
            self.font.setPointSize(size)
        if bold is not None:
            self.font.setWeight(
                QFont.Weight.Bold if bold else QFont.Weight.Normal
            )
        self.item.setFont(self.font)

    def set_text_color(self, color: QColor):
        self.item.setDefaultTextColor(color)

    def set_glow(self, color=None, blur=None, alpha=None, offset_x=None, offset_y=None):
        if color:
            self.glow_color = QColor(color)
        if alpha is not None:
            self.glow_color.setAlpha(alpha)
        self.glow.setColor(self.glow_color)

        if blur is not None:
            self.glow.setBlurRadius(blur)
        if offset_x is not None or offset_y is not None:
            self.glow.setOffset(offset_x or 0, offset_y or 0)