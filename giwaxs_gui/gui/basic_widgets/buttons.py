# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (QAbstractButton, QGraphicsDropShadowEffect,
                             QHBoxLayout, QLabel, QWidget)
from PyQt5.QtGui import (QIcon, QPainter, QBrush, QColor)
from PyQt5.QtCore import Qt, QRect, pyqtSignal

from ...utils import Icon

logger = logging.getLogger(__name__)


class RoundedPushButton(QAbstractButton):
    def __init__(self,
                 parent=None, *,
                 text: str = '',
                 icon: QIcon = None,
                 radius: int = 20,
                 background_color: QColor or str = 'white'):
        self._radius = radius
        self._text = text
        self._icon = icon
        if isinstance(background_color, str):
            if background_color == 'transparent':
                background_color = QColor(0, 0, 0, 0)
            else:
                background_color = QColor(background_color)
        self._background_color = background_color
        super().__init__(parent)
        self.__init_shadow__()
        self._pressed = False
        if self._icon:
            self.setFixedSize(self._radius, self._radius)

    def __init_shadow__(self):
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(self._radius)
        self.shadow.setXOffset(3)
        self.shadow.setYOffset(3)
        self.setGraphicsEffect(self.shadow)

    def _get_painter(self):
        painter = QPainter(self)
        brush = QBrush()
        brush.setColor(self._background_color)
        brush.setStyle(Qt.SolidPattern)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.setRenderHint(QPainter.Antialiasing)
        return painter

    def paintEvent(self, QPaintEvent):
        painter = self._get_painter()
        if self._pressed:
            rect = QRect(0, 3, painter.device().width(),
                         int(painter.device().height() * 0.9))
        else:
            rect = QRect(0, 0, painter.device().width(),
                         painter.device().height())
        painter.drawRoundedRect(rect, self._radius, self._radius)
        if self._icon:
            pixmap = self._icon.pixmap(self.size())
            painter.drawPixmap(0, 0, pixmap)

    def mousePressEvent(self, QMouseEvent):
        self._pressed = True
        super().mousePressEvent(QMouseEvent)
        if QMouseEvent.button() == Qt.LeftButton:
            self._pressed = True
            self.shadow.setEnabled(False)

    def mouseReleaseEvent(self, QMouseEvent):
        self._pressed = False
        super().mouseReleaseEvent(QMouseEvent)
        self.shadow.setEnabled(True)
        self.shadow.setBlurRadius(self._radius)


class ConfirmButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, icon: QIcon, parent=None, radius: float = 30,
                 smaller_radius: float = 25,
                 text: str = ''):
        QWidget.__init__(self, parent)
        self._icon = icon
        self._text = text
        self._status = None
        self.__init_ui__(radius, smaller_radius)
        self.hide_and_show('icon')

    def __init_ui__(self, radius, smaller_radius):
        layout = QHBoxLayout(self)
        self.setLayout(layout)

        self.icon_widget = RoundedPushButton(self, icon=self._icon,
                                             radius=radius)
        self.icon_widget.clicked.connect(self.on_clicked)
        layout.addWidget(self.icon_widget)

        self.label_widget = QLabel(self._text)
        self.confirm = RoundedPushButton(
            icon=Icon('confirm'), radius=smaller_radius)
        self.confirm.clicked.connect(self.on_clicked)
        self.confirm.clicked.connect(self.clicked.emit)
        self.decline = RoundedPushButton(
            icon=Icon('delete'), radius=smaller_radius)
        self.decline.clicked.connect(self.on_clicked)
        layout.addWidget(self.label_widget)
        layout.addWidget(self.confirm)
        layout.addWidget(self.decline)

    def on_clicked(self):
        self.hide_and_show()

    def hide_and_show(self, new_status: str = None):
        if new_status in 'icon question'.split():
            self._status = new_status
        else:
            self._status = 'icon' if self._status == 'question' else 'question'

        if self._status == 'icon':
            self.label_widget.hide()
            self.confirm.hide()
            self.decline.hide()
            self.icon_widget.show()
        else:
            self.label_widget.show()
            self.confirm.show()
            self.decline.show()
            self.icon_widget.hide()


class DeleteButton(ConfirmButton):
    def __init__(self, parent=None, radius: float = 30,
                 smaller_radius: float = 25, text: str = 'Delete?'):
        ConfirmButton.__init__(self, Icon('delete'), parent,
                               radius, smaller_radius, text=text)


class InfoButton(RoundedPushButton):
    def __init__(self, info, parent=None):
        RoundedPushButton.__init__(self, parent, icon=Icon('info'))
        self.setToolTip(info)
