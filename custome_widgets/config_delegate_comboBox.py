from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QColor

class ConfigDelegateComboBox(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        painter.save()
        style = QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter)

        text_color = option.palette.highlightedText().color() if option.state & QtWidgets.QStyle.StateFlag.State_Selected else option.palette.text().color()
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        user = index.data(Qt.ItemDataRole.UserRole) or {}
        gb, days = "", ""
        if isinstance(user, dict):
            gb = user.get("gb", "")
            days = user.get("days", "")
        elif isinstance(user, (list, tuple)) and len(user) >= 2:
            gb, days = user[0], user[1]

        sub_parts = []
        if gb != "":
            sub_parts.append(f"{gb} GB Left")
        if days != "":
            try:
                days_val = float(days)
            except Exception:
                days_val = days
            if isinstance(days_val, (int, float)) and days_val <= 0:
                sub_parts.append("expired")
            elif isinstance(days_val, (int, float)) and days_val > 0:
                sub_parts.append(f"{days} Days Left")
            elif str(days).lower() == "expired":
                sub_parts.append("expired")
        subtext = " | ".join(sub_parts)

        rect = option.rect.adjusted(6, 4, -6, -4)
        main_font = option.font
        bold_font = QtGui.QFont(main_font)
        bold_font.setBold(True)
        painter.setFont(bold_font)
        painter.setPen(text_color)
        fm_main = painter.fontMetrics()
        main_h = fm_main.height()
        painter.drawText(QRect(rect.left(), rect.top(), rect.width(), main_h),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, str(name))

        sub_font = QtGui.QFont(main_font)
        sub_font.setPointSize(max(8, sub_font.pointSize() - 2))
        painter.setFont(sub_font)
        sub_color = option.palette.highlightedText().color() if option.state & QtWidgets.QStyle.StateFlag.State_Selected else QColor(148, 163, 184)
        painter.setPen(sub_color)
        fm_sub = painter.fontMetrics()
        sub_y = rect.top() + main_h
        painter.drawText(QRect(rect.left(), sub_y, rect.width(), fm_sub.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, subtext)
        painter.restore()

    def sizeHint(self, option, index):
        font = option.font
        fm = QtGui.QFontMetrics(font)
        h = fm.height() * 2 + 8
        return QSize(option.rect.width(), h)