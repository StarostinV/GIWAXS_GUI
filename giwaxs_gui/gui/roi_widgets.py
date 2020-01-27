import logging
import weakref
from typing import Union
from functools import wraps
from abc import abstractmethod
import numpy as np

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLineEdit,
                             QMenu, QGridLayout, QWidgetAction)

from PyQt5.QtGui import (QColor, QPainter, QPen, QPainterPath,
                         QCursor, QStandardItem)
from PyQt5.QtCore import (pyqtSignal, QRectF, Qt,
                          QItemSelectionModel, QObject)

from pyqtgraph import (LinearRegionItem,
                       RectROI, ROI)

from .signal_connection import (SignalConnector,
                                SignalContainer,
                                StatusChangedContainer, AppNode)
from .basic_widgets import (DeleteButton, ControlSlider, RoundedPushButton)
from ..utils import RoiParameters, Icon
# TODO: split into several files.
logger = logging.getLogger(__name__)


# TODO: wrap into class and provide option for customization and changing colors
ACTIVE_COLOR = QColor(255, 139, 66, 70)
ACTIVE_COLOR_BRIGHT = QColor(255, 139, 66)
INACTIVE_COLOR = QColor(0, 0, 255, 50)
INACTIVE_COLOR_BRIGHT = QColor(0, 0, 255)  # QColor(83, 139, 190)
FIXED_COLOR = QColor(0, 255, 0, 50)
FIXED_COLOR_BRIGHT = QColor(0, 255, 0)
FIXED_ACTIVE_COLOR = QColor(255, 0, 255, 50)
FIXED_ACTIVE_COLOR_BRIGHT = QColor(255, 0, 255)


class AbstractRoiContextMenu(QMenu):
    @property
    def roi(self):
        return self._roi()

    def __init__(self, roi: 'AbstractROI'):
        QMenu.__init__(self)
        self.value = roi.value
        self._roi = weakref.ref(roi)
        self.__init_menu__()
        self.exec_(QCursor.pos())

    def send(self, signal: Union[SignalContainer, str, tuple]):
        if not self.roi:
            return
        if isinstance(signal, str):
            self.roi.signal_by_key.emit((signal,))
        elif isinstance(signal, tuple):
            self.roi.signal_by_key.emit(signal)
        else:
            self.roi.arbitrary_signal.emit(signal)

    @abstractmethod
    def __init_menu__(self):
        pass


class RoiContextMenu(AbstractRoiContextMenu):
    def __init_menu__(self):
        self.__init_rename_menu__()
        self.addSeparator()
        self.__init_type_menu__()
        self.addSeparator()
        self.__init_fix_menu__()
        self.addSeparator()
        self.__init_select_menu__()
        self.addSeparator()
        self.__init_delete_menu__()

    def __init_fix_menu__(self):
        fix_menu = self.addMenu('Fix/Unfix')
        if not self.value.movable:
            fix_action = fix_menu.addAction('Unfix roi')
            fix_action.triggered.connect(
                lambda: self.send(SignalContainer().segment_unfixed(self.value)))
        else:
            fix_action = fix_menu.addAction('Fix roi')
            fix_action.triggered.connect(
                lambda: self.send(SignalContainer().segment_fixed(self.value)))
        fix_selected = fix_menu.addAction('Fix selected roi')
        fix_selected.triggered.connect(
            lambda: self.send('fix_selected'))
        unfix_selected = fix_menu.addAction('Unfix selected roi')
        unfix_selected.triggered.connect(
            lambda: self.send('unfix_selected'))

        fix_all = fix_menu.addAction('Fix all roi')
        fix_all.triggered.connect(
            lambda: self.send('fix_all'))

        unfix_all = fix_menu.addAction('Unix all roi')
        unfix_all.triggered.connect(
            lambda: self.send('unfix_all'))

    def __init_delete_menu__(self):
        delete_menu = self.addMenu('Delete')
        delete_self = delete_menu.addAction('Delete this roi')
        delete_self.triggered.connect(
            lambda: self.send(SignalContainer().segment_deleted(self.value)))
        delete_selected = delete_menu.addAction('Delete selected')
        delete_selected.triggered.connect(
            lambda: self.send('delete_selected'))

    def __init_select_menu__(self):
        select_menu = self.addMenu('Select')
        select_all = select_menu.addAction('Select all')
        select_all.triggered.connect(
            lambda: self.send('select_all'))
        unselect_all = select_menu.addAction('Unselect all')
        unselect_all.triggered.connect(
            lambda: self.send('unselect_all'))

    def __init_rename_menu__(self):
        rename = self.addMenu('Rename')
        rename_action = QWidgetAction(self)
        line_edit = QLineEdit(self.value.name)
        line_edit.editingFinished.connect(
            lambda: self.roi.send_name(line_edit.text())
        )
        rename_action.setDefaultWidget(line_edit)
        rename.addAction(rename_action)

    def __init_type_menu__(self):
        if self.value.type == RoiParameters.roi_types.ring:
            new_type = RoiParameters.roi_types.segment
            change_type_name = 'segment'
        else:
            new_type = RoiParameters.roi_types.ring
            change_type_name = 'ring'
        new_value = self.value._replace(type=new_type)
        change_type_action = self.addAction(f'Change type to {change_type_name}')
        change_type_action.triggered.connect(
            lambda: self.send(('change_roi_type', new_value)))


class RadialProfileContextMenu(RoiContextMenu):
    def __init_menu__(self):
        self.__init_rename_menu__()
        self.addSeparator()
        self.__init_type_menu__()
        self.addSeparator()
        self.__init_fix_menu__()
        self.addSeparator()
        self.__init_select_menu__()
        self.addSeparator()
        self.__init_fit_menu__()
        self.addSeparator()
        self.__init_delete_menu__()

    def __init_fit_menu__(self):
        fit_menu = self.addMenu('Fit')
        fit_selected = fit_menu.addAction('Fit selected (separately)')
        fit_selected.triggered.connect(lambda: self.send('fit_selected'))
        fit_together = fit_menu.addAction('Fit selected (together)')
        fit_together.triggered.connect(lambda: self.send('fit_together'))


class AbstractROIContainer(AppNode):
    def __init__(self, signal_connector: SignalConnector):
        AppNode.__init__(self, signal_connector)
        self.signal_connector.downwardSignal.connect(self.process_signal)
        self.roi_dict = dict()

    def process_signal(self, s: SignalContainer):
        for signal in s.segment_created():
            self.add_roi(signal())
        for signal in s.segment_moved():
            self.roi_dict[signal().key].value = signal()
        for signal in s.segment_deleted():
            self.delete_roi(signal())
        for signal in s.segment_fixed():
            self.roi_dict[signal().key].set_fixed()
        for signal in s.segment_unfixed():
            self.roi_dict[signal().key].set_unfixed()
        for signal in s.status_changed():
            self._on_status_changed(signal())
        for signal in s.name_changed():
            self.roi_dict[signal().key].set_name(signal().name)
        for signal in s.type_changed():
            self.on_type_changed(signal())

    @abstractmethod
    def _get_roi(self, params: RoiParameters) -> 'AbstractROI':
        pass

    @abstractmethod
    def _add_item(self, roi: 'AbstractROI'):
        pass

    @abstractmethod
    def _remove_item(self, roi: 'AbstractROI'):
        pass

    def _on_status_changed(self, sig: StatusChangedContainer):
        if not sig.status:
            for k in sig.keys:
                self.roi_dict[k].set_inactive()
        else:
            for k in sig.keys:
                self.roi_dict[k].set_active()

    def emit_create_segment(self, params: RoiParameters):
        self.signal_connector.emit_upward(
            SignalContainer().segment_created(params))

    def emit_delete_segment(self, params: RoiParameters):
        self.signal_connector.emit_upward(
            SignalContainer().segment_deleted(params))

    def emit_status_changed(self, sig: StatusChangedContainer):
        if (not sig.status and
                len(sig.keys) == 1 and
                set([roi.key for roi in self.get_selected()]).difference(sig.keys)):
            sig = sig._replace(status=True, change_others=True)
        SignalContainer(app_node=self).status_changed(sig).send()

    def add_roi(self, params: RoiParameters):
        roi = self._get_roi(params)
        if roi:
            roi.value_changed.connect(self.send_value_changed)
            roi.status_changed.connect(self.emit_status_changed)
            roi.arbitrary_signal.connect(self.signal_connector.emit_upward)
            self.roi_dict[params.key] = roi
            self._add_item(roi)
            return roi

    def delete_roi(self, params: RoiParameters):
        roi = self.roi_dict.pop(params.key)
        self._remove_item(roi)
        roi.deleteLater()

    def get_selected(self):
        return [roi.parameters for roi in self.roi_dict.values() if roi.active]

    def send_value_changed(self, value: RoiParameters):
        SignalContainer(app_node=self).segment_moved(value).send()

    def on_type_changed(self, value: RoiParameters):
        self.roi_dict[value.key].value = value


class KeySignalNameError(ValueError):
    pass


class BasicROIContainer(AbstractROIContainer):
    def add_roi(self, params: RoiParameters):
        roi = AbstractROIContainer.add_roi(self, params)
        if roi:
            roi.signal_by_key.connect(self.resend_key_signal)
        return roi

    def resend_key_signal(self, key: tuple):
        key, args = key[0], key[1:]
        method = getattr(self, key, None)
        if not method:
            raise KeySignalNameError()
        method(*args)

    def fix_selected(self):
        sc = SignalContainer(app_node=self)
        for selected in self.get_selected():
            sc.segment_fixed(selected)
        sc.send()

    def unfix_selected(self):
        sc = SignalContainer(app_node=self)
        for selected in self.get_selected():
            sc.segment_unfixed(selected)
        sc.send()

    def fix_all(self):
        sc = SignalContainer(app_node=self)
        for roi in self.roi_dict.values():
            sc.segment_fixed(roi.parameters)
        sc.send()

    def unfix_all(self):
        sc = SignalContainer(app_node=self)
        for roi in self.roi_dict.values():
            sc.segment_unfixed(roi.parameters)
        sc.send()

    def delete_selected(self):
        sc = SignalContainer(app_node=self)
        for selected in self.get_selected():
            sc.segment_deleted(selected)
        sc.send()

    def select_all(self):
        sc = SignalContainer(app_node=self)
        keys = list(self.roi_dict.keys())
        sc.status_changed(StatusChangedContainer(keys, True, False))
        sc.send()

    def unselect_all(self):
        sc = SignalContainer(app_node=self)
        keys = list(self.roi_dict.keys())
        sc.status_changed(StatusChangedContainer(keys, False, False))
        sc.send()

    def change_roi_type(self, value: RoiParameters):
        self.on_type_changed(value)
        SignalContainer(app_node=self).type_changed(value).send()


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


class AbstractROI(object):
    value_changed = pyqtSignal(RoiParameters)
    status_changed = pyqtSignal(StatusChangedContainer)
    arbitrary_signal = pyqtSignal(SignalContainer)
    signal_by_key = pyqtSignal(tuple)

    _USE_BRIGHT_COLOR = False

    @property
    def color(self):
        value = self.parameters
        if value.movable and self._active:
            return ACTIVE_COLOR_BRIGHT if self._USE_BRIGHT_COLOR else ACTIVE_COLOR
        if value.movable and not self._active:
            return INACTIVE_COLOR_BRIGHT if self._USE_BRIGHT_COLOR else INACTIVE_COLOR
        if not value.movable and self._active:
            return FIXED_ACTIVE_COLOR_BRIGHT if self._USE_BRIGHT_COLOR else FIXED_ACTIVE_COLOR
        if not value.movable and not self._active:
            return FIXED_COLOR_BRIGHT if self._USE_BRIGHT_COLOR else FIXED_COLOR

    def __init__(self, value: RoiParameters):
        self.parameters = value
        self.key = value.key
        self._active = False

    def init_roi(self):
        self.set_inactive()
        self.set_value(self.parameters)
        if not self.parameters.movable:
            self.set_fixed()

    @property
    def active(self):
        return self._active

    @property
    @abstractmethod
    def value(self):
        """
        Value is an instance of RoiParameters class.
        :return:
        """
        pass

    @value.setter
    @abstractmethod
    def value(self, value: RoiParameters):
        """
        Value is an instance of RoiParameters class.
        :param value: RoiParameters
        :return:
        """
        pass

    def set_value(self, value):
        if self.value != value:
            self.value = value

    @abstractmethod
    def set_active(self):
        pass

    @abstractmethod
    def set_inactive(self):
        pass

    def change_active(self, change_others: bool = True):
        if self._active:
            self.send_inactive()
        else:
            self.send_active(change_others)

    @abstractmethod
    def set_fixed(self):
        pass

    @abstractmethod
    def set_unfixed(self):
        pass

    def send_value(self):
        self.value_changed.emit(self.value)

    def send_active(self, change_others: bool = True):
        self.status_changed.emit(StatusChangedContainer(
            [self.key], True, change_others))

    def send_name(self, name: str, **kwargs):
        self.set_name(name)
        self.arbitrary_signal.emit(SignalContainer().name_changed(self.value, **kwargs))

    def set_name(self, name: str):
        self.parameters = self.parameters._replace(name=name)
        # logger.debug(self.value)

    def send_inactive(self):
        self.status_changed.emit(StatusChangedContainer(
            [self.key], False))

    def send_signal(self, signal_container: SignalContainer):
        self.arbitrary_signal.emit(signal_container)

    def __repr__(self):
        return str(self.parameters)


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
