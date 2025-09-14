# custome_widgets/fancy_round_button.py
from PyQt6 import QtCore, QtGui, QtWidgets

try:
    from PyQt6.QtSvg import QSvgRenderer
    SVG_AVAILABLE = True
except Exception:
    QSvgRenderer = None
    SVG_AVAILABLE = False


class FancyRoundButton(QtWidgets.QPushButton):
    """
    Circular fancy button with pre-rendered blurred halo (donut-shaped).
    Supports animated glow + animated gradient colors per state.
    """
    def __init__(self, parent=None, diameter: int = 200, svg_path: str | None = None,
                 icon_pixmap: QtGui.QPixmap | None = None,
                 halo_color: QtGui.QColor = QtGui.QColor(255, 255, 255),
                 halo_alpha: int = 220,
                 halo_scale: float = 1.25,
                 halo_blur_factor: float = 0.35,
                 halo_inner_ratio: float = 0.45,
                 ring_color: QtGui.QColor | None = None,
                 ring_width: int | None = None):
        super().__init__(parent)
        self._diameter = int(diameter)
        self.setFixedSize(self._diameter, self._diameter)
        self.setFlat(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

        self.svg_path = svg_path
        self._pixmap = icon_pixmap
        self._svg_renderer = None
        if self.svg_path and SVG_AVAILABLE:
            try:
                self._svg_renderer = QSvgRenderer(self.svg_path)
            except Exception:
                self._svg_renderer = None

        # halo params
        self.halo_color = QtGui.QColor(halo_color)
        self.halo_alpha = int(halo_alpha)
        self.halo_pixmap = None
        self.halo_scale = float(halo_scale)
        self.halo_blur_factor = float(halo_blur_factor)
        self.halo_inner_ratio = float(halo_inner_ratio)

        # ring params
        if ring_color is None:
            self.ring_color = QtGui.QColor(255, 255, 255)
        else:
            self.ring_color = QtGui.QColor(ring_color)
        if ring_width is None:
            self.ring_width = max(8, self._diameter // 25)
        else:
            self.ring_width = int(ring_width)

        # gradient colors (animatable)
        self._inner_color = QtGui.QColor(107, 114, 128)   # gray center
        self._outer_color = QtGui.QColor(150, 158, 168)   # gray border
        self.icon_scale = 0.46

        # animation/state
        self._glow_strength = 1.0
        self._state = "disconnected"
        self._pulse_anim = None

        self._update_mask()
        self.update_halo()

    # ---------- animatable property: glow ----------
    def get_glow_strength(self):
        return self._glow_strength
    def set_glow_strength(self, v):
        self._glow_strength = float(v)
        self.update()
    glow_strength = QtCore.pyqtProperty(float, fget=get_glow_strength, fset=set_glow_strength)

    # ---------- animatable properties: colors ----------
    def get_inner_color(self):
        return self._inner_color
    def set_inner_color(self, c):
        self._inner_color = QtGui.QColor(c)
        self.update()
    inner_color = QtCore.pyqtProperty(QtGui.QColor, fget=get_inner_color, fset=set_inner_color)

    def get_outer_color(self):
        return self._outer_color
    def set_outer_color(self, c):
        self._outer_color = QtGui.QColor(c)
        self.update()
    outer_color = QtCore.pyqtProperty(QtGui.QColor, fget=get_outer_color, fset=set_outer_color)

    # ---------- sizing and mask ----------
    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        self._diameter = min(self.width(), self.height())
        self.setFixedSize(self._diameter, self._diameter)
        if self.ring_width != 0:
            self.ring_width = max(6, self._diameter // 25)
        self._update_mask()
        self.update_halo()

    def _update_mask(self):
        r = self._diameter
        path = QtGui.QPainterPath()
        path.addEllipse(0, 0, r, r)
        region = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    # ---------- improved halo generation ----------
    def update_halo(self):
        d = self._diameter
        if d <= 0:
            return

        halo_radius = d * self.halo_scale
        pix_w = int(halo_radius * 2)
        pix_h = int(halo_radius * 2)

        base = QtGui.QPixmap(pix_w, pix_h)
        base.fill(QtCore.Qt.GlobalColor.transparent)
        p = QtGui.QPainter(base)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        color = QtGui.QColor(self.halo_color)
        color.setAlpha(self.halo_alpha)
        p.setBrush(QtGui.QBrush(color))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.drawEllipse(QtCore.QRectF(0, 0, pix_w, pix_h))

        inner_d = pix_w * self.halo_inner_ratio
        cx = pix_w / 2.0
        cy = pix_h / 2.0
        p.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Clear)
        p.drawEllipse(QtCore.QRectF(cx - inner_d / 2.0, cy - inner_d / 2.0, inner_d, inner_d))
        p.end()

        blur_radius = max(6.0, d * self.halo_blur_factor)
        scene = QtWidgets.QGraphicsScene()
        item = QtWidgets.QGraphicsPixmapItem(base)
        blur = QtWidgets.QGraphicsBlurEffect()
        blur.setBlurRadius(blur_radius)
        item.setGraphicsEffect(blur)
        scene.addItem(item)

        result = QtGui.QPixmap(pix_w, pix_h)
        result.fill(QtCore.Qt.GlobalColor.transparent)
        r_painter = QtGui.QPainter(result)
        r_painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        scene.render(r_painter,
                     QtCore.QRectF(0, 0, pix_w, pix_h),
                     QtCore.QRectF(0, 0, pix_w, pix_h))
        r_painter.end()

        self.halo_pixmap = result

    # ---------- paint ----------
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        r = min(w, h) / 2.0
        center = QtCore.QPointF(w / 2.0, h / 2.0)

        # halo
        if self.halo_pixmap is not None and not self.halo_pixmap.isNull():
            painter.save()
            painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Plus)
            halo_w = self.halo_pixmap.width()
            halo_h = self.halo_pixmap.height()
            target_size = QtCore.QSizeF(r * 2 * self.halo_scale, r * 2 * self.halo_scale)
            target_rect = QtCore.QRectF(center.x() - target_size.width() / 2.0,
                                        center.y() - target_size.height() / 2.0,
                                        target_size.width(),
                                        target_size.height())
            painter.setOpacity(max(0.0, min(1.6, self._glow_strength)))
            painter.drawPixmap(target_rect, self.halo_pixmap,
                               QtCore.QRectF(0, 0, halo_w, halo_h))
            painter.restore()

        # base circle (linear gradient)
        base_grad = QtGui.QLinearGradient(0, 0, 0, h)
        base_grad.setColorAt(0.0, self._inner_color)
        base_grad.setColorAt(1.0, self._outer_color)
        painter.setBrush(base_grad)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        inner_rect = QtCore.QRectF(center.x() - r * 0.85,
                                   center.y() - r * 0.85,
                                   (r * 0.85) * 2, (r * 0.85) * 2)
        painter.drawEllipse(inner_rect)

        # ring
        if self.ring_width > 0 and self.ring_color.alpha() > 0:
            pen = QtGui.QPen(self.ring_color)
            pen.setWidthF(self.ring_width)
            pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            ring_rect = QtCore.QRectF(center.x() - r * 0.9,
                                      center.y() - r * 0.9,
                                      (r * 0.9) * 2, (r * 0.9) * 2)
            painter.drawEllipse(ring_rect)

        # icon
        if self._svg_renderer is not None and self._svg_renderer.isValid():
            icon_d = r * 2 * self.icon_scale
            icon_rect = QtCore.QRectF(center.x() - icon_d / 2.0,
                                      center.y() - icon_d / 2.0,
                                      icon_d, icon_d)
            try:
                self._svg_renderer.render(painter, icon_rect)
            except Exception:
                pass
        elif self._pixmap is not None and not self._pixmap.isNull():
            icon_d = int(r * 2 * self.icon_scale)
            scaled = self._pixmap.scaled(icon_d, icon_d,
                                         QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                         QtCore.Qt.TransformationMode.SmoothTransformation)
            ix = int(center.x() - scaled.width() / 2)
            iy = int(center.y() - scaled.height() / 2)
            painter.drawPixmap(ix, iy, scaled)

        painter.end()

    # ---------- animatable property: halo color ----------
    def get_halo_qcolor(self):
        return self.halo_color
    def set_halo_qcolor(self, c):
        self.halo_color = QtGui.QColor(c)
        self.update_halo()
        self.update()
    halo_qcolor = QtCore.pyqtProperty(QtGui.QColor, fget=get_halo_qcolor, fset=set_halo_qcolor)

    # ---------- helper: animate colors ----------
    def animate_colors(self, inner_target: QtGui.QColor, outer_target: QtGui.QColor,
                       halo_target: QtGui.QColor):
        anim1 = QtCore.QPropertyAnimation(self, b"inner_color")
        anim1.setDuration(600)
        anim1.setStartValue(self._inner_color)
        anim1.setEndValue(inner_target)

        anim2 = QtCore.QPropertyAnimation(self, b"outer_color")
        anim2.setDuration(600)
        anim2.setStartValue(self._outer_color)
        anim2.setEndValue(outer_target)

        anim3 = QtCore.QPropertyAnimation(self, b"halo_qcolor")
        anim3.setDuration(600)
        anim3.setStartValue(self.halo_color)
        anim3.setEndValue(halo_target)

        group = QtCore.QParallelAnimationGroup(self)
        group.addAnimation(anim1)
        group.addAnimation(anim2)
        group.addAnimation(anim3)
        group.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._pulse_anim = group

    # ---------- state ----------
    def set_state(self, state: str):
        state = str(state)
        if state == self._state:
            return
        self._state = state

        if self._pulse_anim is not None:
            try:
                self._pulse_anim.stop()
            except Exception:
                pass
            self._pulse_anim = None

        if state == "disconnected":
            self.animate_colors(QtGui.QColor("#6B7280"), QtGui.QColor("#9CA3AF"), QtGui.QColor("#9CA3AF"))
            self.set_glow_strength(0.6)

        elif state == "connecting":
            # animate to yellow/orange
            self.animate_colors(QtGui.QColor("#FBBF24"), QtGui.QColor("#F59E0B"), QtGui.QColor("#F59E0B"))

            anim = QtCore.QPropertyAnimation(self, b"glow_strength")
            anim.setStartValue(0.6)
            anim.setKeyValueAt(0.5, 1.6)
            anim.setEndValue(0.6)
            anim.setDuration(1100)
            anim.setLoopCount(-1)
            anim.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
            self._pulse_anim = anim

        elif state == "connected":
            # animate to green/blue
            self.animate_colors(QtGui.QColor("#22C55E"), QtGui.QColor("#06B6D4"), QtGui.QColor("#06B6D4"))

            seq = QtCore.QSequentialAnimationGroup(self)
            a1 = QtCore.QPropertyAnimation(self, b"glow_strength")
            a1.setStartValue(0.6)
            a1.setEndValue(1.6)
            a1.setDuration(300)
            a2 = QtCore.QPropertyAnimation(self, b"glow_strength")
            a2.setStartValue(1.6)
            a2.setEndValue(1.0)
            a2.setDuration(300)
            seq.addAnimation(a1)
            seq.addAnimation(a2)
            seq.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
            self._pulse_anim = seq

        elif state == "error":
            orig = self.halo_color
            self.halo_color = QtGui.QColor(255, 0, 0)
            self.update_halo()
            anim = QtCore.QPropertyAnimation(self, b"glow_strength")
            anim.setStartValue(1.6)
            anim.setEndValue(0.6)
            anim.setDuration(700)
            anim.setLoopCount(1)
            def restore():
                self.halo_color = orig
                self.update_halo()
            anim.finished.connect(restore)
            anim.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
            self._pulse_anim = anim

        if state in ("connecting", "connected"):
            self.halo_alpha = min(255, max(100, self.halo_alpha))
            self.update_halo()
        else:
            self.halo_alpha = max(80, min(255, self.halo_alpha))
            self.update_halo()
        self.update()
