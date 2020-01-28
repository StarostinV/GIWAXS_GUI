# -*- coding: utf-8 -*-
import weakref
from functools import wraps

import numpy as np

from PyQt5.QtCore import QObject, Qt, QRectF, pyqtSignal, QItemSelectionModel
from PyQt5.QtGui import QPainter, QPen, QPainterPath, QStandardItem, QColor
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QGridLayout

from pyqtgraph import LinearRegionItem, RectROI, ROI

from .abstract_roi_widget import AbstractROI
from .roi_menu import RadialProfileContextMenu, RoiContextMenu
from ..basic_widgets import ControlSlider, RoundedPushButton, DeleteButton
from ...utils import RoiParameters, Icon


def set_fixed_decorator(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.parameters = self.parameters._replace(movable=False)
        # self.set_inactive()
        return func(self, *args, **kwargs)

    return wrapper


def set_unfixed_decorator(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.parameters = self.parameters._replace(movable=True)
        # self.set_inactive()
        return func(self, *args, **kwargs)

    return wrapper


class EmptyROI(AbstractROI, QObject):
    def __init__(self, value: RoiParameters, *args, **kwargs):
        AbstractROI.__init__(self, value)
        QObject.__init__(self, *args, **kwargs)
        self.init_roi()

    @property
    def value(self):
        return self.parameters

    @value.setter
    def value(self, value: RoiParameters):
        self.parameters = value

    def set_active(self):
        pass

    def set_inactive(self):
        pass

    def set_fixed(self):
        pass

    def set_unfixed(self):
        pass


class Roi1D(AbstractROI, LinearRegionItem):
    _ACTIVE_Z = -15
    _INACTIVE_Z = -25
    _FIXED_Z = -30

    def __init__(self, value: RoiParameters, *args, **kwargs):
        AbstractROI.__init__(self, value)
        LinearRegionItem.__init__(self, *args, **kwargs)
        self.sigRegionChanged.connect(self.roi_is_moving)
        self.init_roi()

    def roi_is_moving(self):
        if self.moving:
            self.send_value()
        for l in self.lines:
            if l.moving:
                self.send_value()

    @property
    def value(self):
        x1, x2 = self.getRegion()
        r, w = (x1 + x2) / 2, x2 - x1
        self.parameters = self.parameters._replace(radius=r, width=w)
        return self.parameters

    @value.setter
    def value(self, value: RoiParameters):
        if value != self.value:
            self.parameters = value
            r, w = value.radius, value.width
            x1, x2 = r - w / 2, r + w / 2
            self.setRegion((x1, x2))

    @set_fixed_decorator
    def set_fixed(self):
        self.setMovable(False)
        self.setZValue(self._FIXED_Z)
        self.setBrush(self.color)
        self.viewRangeChanged()

    @set_unfixed_decorator
    def set_unfixed(self):
        self.setMovable(True)
        self.setBrush(self.color)
        self.viewRangeChanged()

    def mouseDragEvent(self, ev):
        if not ev.modifiers() == Qt.ShiftModifier:
            LinearRegionItem.mouseDragEvent(self, ev)
        else:
            self.mouseClickEvent(ev)

    def mouseClickEvent(self, ev):
        if self.moving and ev.button() == Qt.RightButton:
            ev.accept()
            for i, l in enumerate(self.lines):
                l.setPos(self.startPositions[i])
            self.moving = False
            self.sigRegionChanged.emit(self)
            self.sigRegionChangeFinished.emit(self)
            self.send_value()
        elif ev.button() == Qt.RightButton:
            ev.accept()
            self.show_context_menu(ev)
        elif ev.button() == Qt.LeftButton and ev.modifiers() == Qt.ShiftModifier:
            ev.accept()
            self.change_active(False)
        elif ev.button() == Qt.LeftButton:
            self.change_active()
        self.viewRangeChanged()

    def show_context_menu(self, ev):
        RadialProfileContextMenu(self)

    def set_active(self):
        self._active = True
        self.setBrush(self.color)
        self.viewRangeChanged()
        self.setZValue(self._ACTIVE_Z)

    def set_inactive(self):
        self._active = False
        self.setBrush(self.color)
        self.viewRangeChanged()
        self.setZValue(self._INACTIVE_Z)


class Roi1DAngular(Roi1D):
    @property
    def value(self):
        x1, x2 = self.getRegion()
        a, a_w = (x1 + x2) / 2, x2 - x1
        self.parameters = self.parameters._replace(angle=a, angle_std=a_w)
        return self.parameters

    @value.setter
    def value(self, value: RoiParameters):
        if value != self.value:
            self.parameters = value
            a, a_w = value.angle, value.angle_std
            x1, x2 = a - a_w / 2, a + a_w / 2
            self.setRegion((x1, x2))


class Roi2DRect(AbstractROI, RectROI):
    _USE_BRIGHT_COLOR = True
    _g = 180 / np.pi

    def __init__(self, value: RoiParameters, rr, r_size, phi, phi_size):
        AbstractROI.__init__(self, value)
        RectROI.__init__(self, pos=(0, 0), size=(1, 1))
        self.__init_ratios__(rr, r_size, phi, phi_size)

        self.init_roi()
        self.handle = self.handles[0]['item']
        self.sigRegionChanged.connect(self.handle_is_moving)

    def __init_ratios__(self, rr, r_size, phi, phi_size):
        _g = self._g
        self.r_ratio = (rr.max() - rr.min()) / r_size
        self.phi_ratio = (phi.max() - phi.min()) / phi_size * _g
        self.r_min = rr.min()
        self.phi_min = phi.min() * _g

    def handle_is_moving(self):
        if self.handle.isMoving:
            self.send_value()

    @property
    def value(self):
        size, pos = self.size(), self.pos()
        w, a_w = size
        r, a = pos[0] + w / 2, pos[1] + a_w / 2
        r *= self.r_ratio + self.r_min
        w *= self.r_ratio + self.r_min
        a *= self.phi_ratio + self.phi_min
        a_w *= self.phi_ratio + self.phi_min
        self.parameters = self.parameters._replace(
            radius=r, width=w, angle=a, angle_std=abs(a_w))
        return self.parameters

    @value.setter
    def value(self, value: RoiParameters):
        if value != self.parameters:
            self.parameters = value
            r, w = (value.radius - self.r_min) / self.r_ratio, (value.width - self.r_min) / self.r_ratio
            a = (value.angle - self.phi_min) / self.phi_ratio
            a_w = abs((value.angle_std - self.phi_min) / self.phi_ratio)

            pos = [r - w / 2, a - a_w / 2]
            size = [w, a_w]
            self.setSize(size)
            self.setPos(pos)

    @set_fixed_decorator
    def set_fixed(self):
        self.translatable = False
        self.setPen(self.color)

    @set_unfixed_decorator
    def set_unfixed(self):
        self.translatable = True
        self.setPen(self.color)

    def mouseDragEvent(self, ev):
        RectROI.mouseDragEvent(self, ev)
        self.send_value()

    def set_active(self):
        self._active = True
        self.setPen(self.color)

    def set_inactive(self):
        self._active = False
        self.setPen(self.color)


class Roi2DRing(AbstractROI, ROI):
    _USE_BRIGHT_COLOR = True

    def __init__(self, value, parent=None):
        self._center = (0, 0)
        self._radius = value.radius
        self._width = value.width
        self._angle = value.angle
        self._angle_std = value.angle_std
        AbstractROI.__init__(self, value)
        ROI.__init__(
            self, self._center,
            (self._radius, self._radius), movable=False, parent=parent)
        self.aspectLocked = True
        self.init_roi()
        self.set_radius(self._radius)

    @property
    def value(self):
        self.parameters = self.parameters._replace(
            radius=self._radius, width=self._width, angle=self._angle,
            angle_std=self._angle_std)
        return self.parameters

    @value.setter
    def value(self, value: RoiParameters):
        if value != self.parameters:
            self.parameters = value
            self.set_radius(value.radius)
            self.set_width(value.width)
            if value.angle is not None:
                self.set_angle(value.angle)
            if value.angle_std is not None:
                self.set_angle_std(value.angle_std)

    def set_active(self):
        self._active = True
        self.setPen(self.color)

    def set_inactive(self):
        self._active = False
        self.setPen(self.color)

    @set_fixed_decorator
    def set_fixed(self):
        self.setPen(self.color)

    @set_unfixed_decorator
    def set_unfixed(self):
        self.setPen(self.color)

    def set_center(self, center: tuple):
        self._center = center
        d = self._radius + self._width / 2
        pos = (center[1] - d, center[0] - d)
        self.setPos(pos)

    def set_radius(self, radius):
        self._radius = radius
        s = 2 * radius + self._width
        self.setSize((s, s))
        self.set_center(self._center)

    def set_width(self, width):
        self._width = width
        self.set_radius(self._radius)

    def set_angle(self, angle):
        self._angle = angle
        self.set_center(self._center)

    def set_angle_std(self, angle):
        self._angle_std = angle
        self.set_center(self._center)

    def paint(self, p, opt, widget):
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(self.currentPen)

        x1, y1 = 0, 0
        x2, y2 = x1 + self._width, y1 + self._width
        x3, y3 = x1 + self._width / 2, y1 + self._width / 2
        d1, d2, d3 = (2 * self._radius + self._width,
                      2 * self._radius - self._width,
                      2 * self._radius)

        # p.scale(self._radius, self._radius)
        r1 = QRectF(x1, y1, d1, d1)
        r2 = QRectF(x2, y2, d2, d2)
        r3 = QRectF(x3, y3, d3, d3)
        angle = - self._angle or 0
        angle_std = self._angle_std or 360
        a1, a2 = ((angle - angle_std / 2) * 16, angle_std * 16)
        p.drawArc(r1, a1, a2)
        p.drawArc(r2, a1, a2)
        dash_pen = QPen(self.currentPen)
        dash_pen.setStyle(Qt.DashLine)
        p.setPen(dash_pen)
        p.drawArc(r3, a1, a2)

    def getArrayRegion(self, arr, img=None, axes=(0, 1), **kwds):
        """
        Return the result of ROI.getArrayRegion()
        masked by the elliptical shape
        of the ROI. Regions outside the ellipse are set to 0.
        """
        # Note: we could use the same method as used by PolyLineROI, but this
        # implementation produces a nicer mask.
        arr = ROI.getArrayRegion(self, arr, img, axes, **kwds)
        if arr is None or arr.shape[axes[0]] == 0 or arr.shape[axes[1]] == 0:
            return arr
        w = arr.shape[axes[0]]
        h = arr.shape[axes[1]]
        ## generate an ellipsoidal mask
        mask = np.fromfunction(
            lambda x, y: (((x + 0.5) / (w / 2.) - 1) ** 2 + ((y + 0.5) / (h / 2.) - 1) ** 2) ** 0.5 < 1, (w, h))

        # reshape to match array axes
        if axes[0] > axes[1]:
            mask = mask.T
        shape = [(n if i in axes else 1) for i, n in enumerate(arr.shape)]
        mask = mask.reshape(shape)

        return arr * mask

    def shape(self):
        self.path = QPainterPath()
        self.path.addEllipse(self.boundingRect())
        return self.path


class RingParametersWidget(AbstractROI, QWidget):
    deleteClicked = pyqtSignal(object)

    @property
    def item(self):
        item = self._item()
        if not item:
            raise LookupError(f'Item is not found.')
        return item

    @property
    def control_widget(self):
        control_widget = self._control_widget()
        if not control_widget:
            raise LookupError(f'Control widget is not found.')
        return control_widget

    @property
    def value(self):
        self.parameters = self.parameters._replace(
            radius=self.radius_slider.value, width=self.width_slider.value
        )
        return self.parameters

    @value.setter
    def value(self, value):
        if value != self.parameters:
            self.radius_slider.set_value(value.radius, True)
            self.width_slider.set_value(value.width, True)

    def __init__(self,
                 model_item: QStandardItem,
                 control_widget: 'ControlWidget',
                 params: RoiParameters,
                 radius_range,
                 width_range,
                 decimals: int = 3
                 ):
        QWidget.__init__(self)
        AbstractROI.__init__(self, params)
        self._item = weakref.ref(model_item)
        self._control_widget = weakref.ref(control_widget)
        self.setup_window = None
        self.name = params.name
        self.__init_ui__(params, radius_range, width_range, decimals)
        self.init_roi()

    def set_name(self, name: str):
        super().set_name(name)
        self.name = name
        self.label.setText(name)

    def __init_ui__(self, params, radius_range, width_range, decimals):
        self.width_slider = ControlSlider('Width', width_range,
                                          params.width,
                                          self, decimals=decimals)
        self.radius_slider = ControlSlider('Radius', radius_range,
                                           params.radius,
                                           self, decimals=decimals)
        self.setup_button = RoundedPushButton(
            icon=Icon('setup_white'), radius=30,
            background_color=QColor(255, 255, 255, 100))
        self.delete_button = DeleteButton(self)
        self.setup_button.clicked.connect(self.open_setup_window)
        self.delete_button.clicked.connect(
            lambda: self.deleteClicked.emit(self.value))
        self.radius_slider.statusChanged.connect(self.on_slider_status_changed)
        self.width_slider.statusChanged.connect(self.on_slider_status_changed)

        self.radius_slider.valueChanged.connect(self.send_value)
        self.width_slider.valueChanged.connect(self.send_value)

        layout = QHBoxLayout(self)
        self.label = QLineEdit(self.name)
        self.label.textEdited.connect(self.send_name)
        self.label.setStyleSheet('QLineEdit {border: none;}')
        self.setLayout(layout)
        layout.addWidget(self.label)
        layout.addWidget(self.radius_slider)
        layout.addWidget(self.width_slider)
        layout.addWidget(self.setup_button)
        layout.addWidget(self.delete_button)

    def on_slider_status_changed(self, status):
        if status == 'show':
            self.send_active()

    def open_setup_window(self):
        RoiContextMenu(self)

    def set_active(self, *args):
        if not self._active:
            self._active = True
            self.control_widget.selectionModel().select(
                self.item.index(), QItemSelectionModel.Select)

    def set_inactive(self):
        if self._active:
            self._active = False
            self.control_widget.selectionModel().select(
                self.item.index(), QItemSelectionModel.Deselect)
            self.radius_slider.hide_and_show('hide')
            self.width_slider.hide_and_show('hide')

    @set_fixed_decorator
    def set_fixed(self):
        self.radius_slider.set_fixed()
        self.width_slider.set_fixed()

    @set_unfixed_decorator
    def set_unfixed(self):
        self.radius_slider.set_unfixed()
        self.width_slider.set_unfixed()


class RingSegmentParametersWidget(RingParametersWidget):
    @property
    def value(self):
        self.parameters = self.parameters._replace(
            radius=self.radius_slider.value, width=self.width_slider.value,
            angle=self.angle_slider.value, angle_std=self.angle_std_slider.value
        )
        return self.parameters

    @value.setter
    def value(self, value):
        if value != self.parameters:
            self.radius_slider.set_value(value.radius, True)
            self.width_slider.set_value(value.width, True)
            self.angle_slider.set_value(value.angle, True)
            self.angle_std_slider.set_value(value.angle_std, True)

    def __init_ui__(self, params, radius_range, width_range, decimals):
        self.width_slider = ControlSlider('Width', width_range,
                                          params.width,
                                          self, decimals=decimals)
        self.radius_slider = ControlSlider('Radius', radius_range,
                                           params.radius,
                                           self, decimals=decimals)
        self.angle_slider = ControlSlider('Angle', (0, 360),
                                          params.angle,
                                          self, decimals=decimals)
        self.angle_std_slider = ControlSlider('Angle width', (0, 360),
                                              params.angle_std,
                                              self, decimals=decimals)
        self.setup_button = RoundedPushButton(
            icon=Icon('setup_white'), radius=30,
            background_color=QColor(255, 255, 255, 100))
        self.delete_button = DeleteButton(self)
        self.setup_button.clicked.connect(self.open_setup_window)
        self.delete_button.clicked.connect(
            lambda: self.deleteClicked.emit(self.value))
        self.radius_slider.statusChanged.connect(self.on_slider_status_changed)
        self.width_slider.statusChanged.connect(self.on_slider_status_changed)
        self.angle_slider.statusChanged.connect(self.on_slider_status_changed)
        self.angle_std_slider.statusChanged.connect(self.on_slider_status_changed)

        self.radius_slider.valueChanged.connect(self.send_value)
        self.width_slider.valueChanged.connect(self.send_value)
        self.angle_slider.valueChanged.connect(self.send_value)
        self.angle_std_slider.valueChanged.connect(self.send_value)

        layout = QGridLayout(self)
        self.label = QLineEdit(self.name)
        self.label.editingFinished.connect(
            lambda: self.set_name(self.label.text())
        )
        self.label.setStyleSheet('QLineEdit {border: none;}')
        self.setLayout(layout)
        layout.addWidget(self.label, 0, 0, 2, 1)
        layout.addWidget(self.radius_slider, 0, 1)
        layout.addWidget(self.angle_slider, 0, 2)
        layout.addWidget(self.width_slider, 1, 1)
        layout.addWidget(self.angle_std_slider, 1, 2)
        layout.addWidget(self.setup_button, 0, 3, 2, 1)
        layout.addWidget(self.delete_button, 0, 4, 2, 1)

    def set_inactive(self):
        if self._active:
            self._active = False
            self.control_widget.selectionModel().select(
                self.item.index(), QItemSelectionModel.Deselect)
            self.radius_slider.hide_and_show('hide')
            self.width_slider.hide_and_show('hide')
            self.angle_slider.hide_and_show('hide')
            self.angle_std_slider.hide_and_show('hide')


class FileWidgetRoi(AbstractROI, QObject):
    _USE_BRIGHT_COLOR = True

    @property
    def item(self):
        return self._item() if self._item else None

    def __init__(self, value: RoiParameters, item: 'PropertiesItem' = None):
        AbstractROI.__init__(self, value)
        QObject.__init__(self)
        self._item = weakref.ref(item) if item else None

    def set_item(self, item: 'PropertiesItem'):
        item.roi = self
        self._item = weakref.ref(item)

    @property
    def value(self):
        return self.parameters

    @value.setter
    def value(self, value: RoiParameters):
        self.parameters = value

    def set_active(self):
        if not self._active:
            self._active = True
            self.item.setData(self.color, Qt.ForegroundRole)

    def set_inactive(self):
        if self._active:
            self._active = False
            self.item.setData(self.color, Qt.ForegroundRole)

    @set_fixed_decorator
    def set_fixed(self):
        self.item.setData(self.color, Qt.ForegroundRole)

    @set_unfixed_decorator
    def set_unfixed(self):
        self.item.setData(self.color, Qt.ForegroundRole)

    def set_name(self, name: str):
        super().set_name(name)
        self.item.setText(name)
