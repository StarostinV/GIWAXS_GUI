# -*- coding: utf-8 -*-
import logging
from abc import abstractmethod
from typing import NamedTuple

import numpy as np
from scipy.ndimage import gaussian_filter1d

from PyQt5.QtWidgets import (QWidget, QMainWindow, QFrame,
                             QSlider, QLineEdit, QHBoxLayout,
                             QLabel, QAbstractButton,
                             QGraphicsDropShadowEffect,
                             QWidgetAction, QMenu, QFormLayout,
                             QPushButton, QRadioButton)
from PyQt5.QtGui import (QIntValidator, QPainter, QBrush, QColor)
from PyQt5.QtCore import Qt, pyqtSignal, QRect

from pyqtgraph import (GraphicsLayoutWidget, setConfigOptions,
                       ImageItem, HistogramLUTItem)

from ..config import read_config, save_config
from ..utils import (color_animation, QIcon, Icon,
                     center_widget, validate_scientific_value)

logger = logging.getLogger(__name__)


class Custom1DPlot(GraphicsLayoutWidget):
    def __init__(self, *args, parent=None):
        super(Custom1DPlot, self).__init__(parent)
        self.plot_item = self.addPlot()
        self.plot_item.setMenuEnabled(False)
        self.plot = self.plot_item.plot(*args)

    def set_data(self, *args):
        self.plot.setData(*args)

    def clear_data(self):
        self.plot_item.clearPlots()

    def set_x(self, x):
        x = np.array(x)
        y = self.plot.yData
        if y.shape != x.shape:
            return
        self.plot.setData(x, y)


class Smooth1DPlot(QMainWindow):
    _MaximumSliderWidth = 200
    _MaximumSliderHeight = 30

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        self._y = value
        self.update_smoothed_y()

    @property
    def smoothed_y(self):
        return self._smoothed_y

    @property
    def x(self):
        if self._x is None and self._y is not None:
            return np.arange(self._y.size)
        else:
            return self._x

    @x.setter
    def x(self, value):
        self._x = value

    def update_smoothed_y(self):
        y = self.y
        if isinstance(y, np.ndarray):
            if self.sigma:
                self._smoothed_y = gaussian_filter1d(y, self.sigma)
            else:
                self._smoothed_y = y

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent=parent)
        self.image_view = Custom1DPlot()
        self.setCentralWidget(self.image_view)
        self.sigma = 0
        self._y = None
        self._smoothed_y = None
        self._x = None
        self.__init_toolbars__()

    def __init_toolbars__(self):
        param_toolbar = self.addToolBar('Parameters')
        param_toolbar.setStyleSheet('background-color: black;')

        self.__init_sigma_slider__(param_toolbar)

    def __init_sigma_slider__(self, toolbar):
        sigma_slider = AnimatedSlider('𝞼', (0, 10), self.sigma,
                                      decimals=2)
        sigma_slider.setMaximumWidth(self._MaximumSliderWidth)
        sigma_slider.setMaximumHeight(self._MaximumSliderHeight)
        sigma_slider.valueChanged.connect(self.update_sigma)
        sigma_slider.setStyleSheet('background-color: white;')
        sigma_slider.shadow.setColor(QColor('blue'))
        self.sigma_slider = sigma_slider
        frame = QFrame()
        layout = QHBoxLayout()
        frame.setLayout(layout)
        frame.setGeometry(0, 0, self._MaximumSliderWidth, toolbar.height() * 0.9)
        layout.addWidget(sigma_slider, alignment=Qt.AlignHCenter)
        toolbar.addWidget(frame)

    def set_sigma(self, value: float):
        self.update_sigma(value)
        self.sigma_slider.set_value(value, change_bounds=True)

    def update_sigma(self, value: float):
        self.sigma = value
        self.update_smoothed_y()
        self.plot()

    def plot(self):
        self.image_view.set_data(self.x, self.smoothed_y)


class CustomImageViewer(GraphicsLayoutWidget):

    def __init__(self, parent=None, **kwargs):
        setConfigOptions(imageAxisOrder='row-major')
        super(CustomImageViewer, self).__init__(parent)
        self._scale = (1., 1.)
        self._center = (0, 0)

        self.__init_ui__()

    def __init_ui__(self):
        self.setWindowTitle('Image Viewer')
        self.image_plot = self.addPlot()
        self.image_plot.vb.setAspectLocked()
        self.image_plot.vb.invertY()
        self.image_item = ImageItem()
        self.image_plot.addItem(self.image_item)
        self.hist = HistogramLUTItem()
        self.hist.setImageItem(self.image_item)
        self.addItem(self.hist)

    def set_data(self, data, change_limits: bool = True, reset_axes: bool = False):
        if data is None:
            return
        self.image_item.setImage(data, change_limits)
        if change_limits:
            self.hist.setLevels(data.min(), data.max())
        if reset_axes:
            self.image_item.resetTransform()
        self.set_default_range()

    def set_default_range(self):
        axes = self.get_axes()
        self.image_plot.setRange(xRange=axes[0], yRange=axes[1])

    def set_auto_range(self):
        self.image_plot.autoRange()

    def set_levels(self, levels=None):
        if levels:
            self.hist.setLevels(levels[0], levels[1])
        else:
            self.hist.setLevels(self.image_item.image.min(),
                                self.image_item.image.max())

    def get_levels(self):
        return self.hist.getLevels()

    def set_center(self, center: tuple, pixel_units: bool = True):
        if not pixel_units:
            scale = self.get_scale()
            center = (center[0] / scale[0], center[1] / scale[1])
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
            self.image_item.scale(*self._scale)
        self.image_item.translate(- center[0], - center[1])
        self._center = center
        self.set_default_range()

    def set_scale(self, scale: float or tuple):
        if isinstance(scale, float) or isinstance(scale, int):
            scale = (scale, scale)
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
        self.image_item.scale(*scale)
        if self._center != (0, 0):
            self.image_item.translate(- self._center[0], - self._center[1])
        self._scale = scale
        self.set_default_range()

    def get_scale(self):
        # scale property is occupied by Qt superclass.
        return self._scale

    def get_center(self):
        return self._center

    def set_x_axis(self, x_min, x_max):
        self._set_axis(x_min, x_max, 0)
        self.set_default_range()

    def set_y_axis(self, y_min, y_max):
        self._set_axis(y_min, y_max, 1)
        self.set_default_range()

    def _set_axis(self, min_: float, max_: float, axis_ind: int):
        shape = self.image_item.image.shape
        scale = np.array(self._scale)
        scale[axis_ind] = (max_ - min_) / shape[axis_ind]
        center = np.array(self._center)
        center[axis_ind] = - min_ / scale[axis_ind]
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
        self.image_item.scale(scale[0], scale[1])
        self.image_item.translate(- center[0], - center[1])
        self._scale = tuple(scale)
        self._center = tuple(center)

    def get_axes(self):
        shape = np.array(self.image_item.image.shape)
        scale = np.array(self._scale)
        min_ = - np.array(self._center) * scale
        max_ = min_ + shape * scale
        return (min_[0], max_[0]), (min_[1], max_[1])


class DoubleSlider(QSlider):
    valueChangedByHand = pyqtSignal(float)

    def __init__(self, *args, decimals: int = 5):
        super().__init__(*args)
        self.decimals = decimals
        self._max_int = 10 ** self.decimals
        self._pressed = False
        self.sliderPressed.connect(self._set_pressed)
        self.sliderReleased.connect(self._set_released)
        self.sliderReleased.connect(self.emit_value)
        self.valueChanged.connect(self._check_and_emit)

        super().setMinimum(0)
        super().setMaximum(self._max_int)

        self._min_value = 0.0
        self._max_value = 1.0

    def emit_value(self, *args):
        self.valueChangedByHand.emit(self.value())

    def _set_pressed(self, *args):
        self._pressed = True

    def _set_released(self, *args):
        self._pressed = False

    def _check_and_emit(self, *args):
        if self._pressed:
            self.emit_value()

    def set_decimals(self, decimals):
        self.decimals = decimals
        value = self.value()
        self._max_int = 10 ** self.decimals
        super().setMinimum(0)
        super().setMaximum(self._max_int)
        self.setRange(self._min_value, self._max_value)
        self.setValue(value)

    def _update_max_int(self):
        self._max_int = self._value_range * (10 ** self.decimals)
        if self._max_int <= 0:
            self._max_int = 1
        super().setMaximum(self._max_int)

    @property
    def _value_range(self):
        return self._max_value - self._min_value

    def _real_to_view(self, value):
        try:
            return int((value - self._min_value) / self._value_range * self._max_int)
        except ZeroDivisionError:
            return 0

    def _view_to_real(self, value):
        return value / self._max_int * self._value_range + self._min_value

    def value(self):
        return self._view_to_real(super().value())

    def setValue(self, value):
        super().setValue(self._real_to_view(value))

    def setMinimum(self, value):
        if value > self._max_value:
            raise ValueError("Minimum limit cannot be higher than maximum")
        real_value = self.value()
        self._min_value = value
        self._update_max_int()
        self.setValue(real_value)
        if real_value < value:
            self.emit_value()

    def setMaximum(self, value):
        if value < self._min_value:
            raise ValueError("Minimum limit cannot be higher than maximum")

        real_value = self.value()
        self._max_value = value
        self._update_max_int()
        self.setValue(real_value)
        if real_value > value:
            self.emit_value()

    def setRange(self, p_int, p_int_1):
        real_value = self.value()
        self._min_value = p_int
        self._max_value = p_int_1
        self._update_max_int()
        self.setValue(real_value)

    def minimum(self):
        return self._min_value

    def maximum(self):
        return self._max_value


class RoundedPushButton(QAbstractButton):
    def __init__(self,
                 parent=None, *,
                 text: str = '',
                 icon: QIcon = None,
                 radius: float = 20,
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
                         painter.device().height() * 0.9)
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


class AnimatedSlider(RoundedPushButton):
    valueChanged = pyqtSignal(float)
    statusChanged = pyqtSignal(str)
    _EditMaximumWidth = 80
    _Height = 40
    _padding = 50

    @property
    def value(self):
        return self.slider.value()

    def __init__(self,
                 name: str,
                 bounds: tuple = (0, 1),
                 value: float = 0,
                 parent=None,
                 orientation=Qt.Horizontal,
                 decimals: int = 0,
                 hide: bool = True,
                 context_menu_enabled: bool = True,
                 disable_changing_status: bool = False,
                 min_max_bounds: tuple = (-10000, 10000)):

        super(AnimatedSlider, self).__init__(parent)
        self.context_menu_enabled = context_menu_enabled
        self.name = name
        self.bounds = bounds
        self._decimals = decimals
        self.init_value = value
        self.__init_ui__(orientation)
        self.clicked.connect(self.on_clicked)
        self._status = 'show'
        self._min_max_bounds = min_max_bounds
        self._disable_changing_status = disable_changing_status
        if hide:
            self.hide_and_show('hide')

    def set_min_max_bounds(self, bounds: tuple):
        if bounds[0] < bounds[1]:
            self._min_max_bounds = bounds

    def on_clicked(self):
        self.hide_and_show()
        self.statusChanged.emit(self._status)

    def contextMenuEvent(self, *args, **kwargs):
        if not self.context_menu_enabled:
            return
        event = args[0]
        menu = QMenu()
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setStyleSheet("QMenu{background:rgba(255, 255, 255, 0%);}")

        decimals_slider = AnimatedSlider(
            'Decimals', (0, 6), self._decimals, hide=False,
            context_menu_enabled=False,
            disable_changing_status=True
        )
        min_slider = AnimatedSlider(
            'Min value', (self._min_max_bounds[0], self.slider.maximum()),
            self.slider.minimum(), hide=False,
            context_menu_enabled=False, disable_changing_status=True)
        max_slider = AnimatedSlider(
            'Max value', (self.slider.minimum(), self._min_max_bounds[1]),
            self.slider.maximum(), hide=False,
            context_menu_enabled=False, disable_changing_status=True)
        decimals_slider.valueChanged.connect(self.set_decimals)
        min_slider.valueChanged.connect(self.slider.setMinimum)
        min_slider.valueChanged.connect(max_slider.slider.setMinimum)
        max_slider.valueChanged.connect(self.slider.setMaximum)

        # TODO: _x - 1e-45 looks like the worst decision ever and should be well tested or better changed.
        max_slider.valueChanged.connect(
            lambda x: min_slider.slider.setMaximum(x - 1e-45))

        for w in [decimals_slider, min_slider, max_slider]:
            w_action = QWidgetAction(self)
            w_action.setDefaultWidget(w)
            menu.addAction(w_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def set_decimals(self, value):
        try:
            value = int(value)
        except ValueError as err:
            logger.exception(err)
            return
        self.slider.set_decimals(value)
        self._decimals = value
        self.editValue.setText(self._get_str_value())
        self._update_label_text()

    def set_bounds(self, bounds: tuple, change_value: bool = False):
        try:
            self.slider.setRange(*bounds)
        except ValueError as err:
            if not change_value:
                logger.exception(err)
            else:
                self.slider.setValue(bounds[0])
                self.slider.setRange(*bounds)

    def hide_and_show(self, new_status: str = None):
        if self._disable_changing_status:
            return
        if new_status in 'show hide'.split():
            self._status = new_status
        else:
            self._status = 'hide' if self._status == 'show' else 'show'

        if self._status == 'hide':
            self.slider.hide()
            self.editValue.hide()
            self._update_label_text()
        else:
            self.slider.show()
            self.editValue.show()
            self.label.setText(self.name)

    def _update_label_text(self, *args):
        if self._status == 'hide':
            new_text = f'{self.name}{" = " if self.name else ""}{self._get_str_value()}'
            self.label.setText(new_text)

    def _get_str_value(self):
        if self._decimals:
            return f'{self.slider.value():.{self._decimals}f}'
        else:
            return str(int(self.slider.value()))

    def set_value(self, value: float, change_bounds: bool = False):
        emit_value = False
        if value < self.slider.minimum():
            if change_bounds:
                self.slider.setMinimum(value)
            else:
                emit_value = True
        if value > self.slider.maximum():
            if change_bounds:
                self.slider.setMaximum(value)
            else:
                emit_value = True
        self.slider.setValue(value)
        self.editValue.setText(self._get_str_value())
        if emit_value:
            self.slider.emit_value()

    def __init_ui__(self, orientation):
        layout = QHBoxLayout(self)

        self.slider = DoubleSlider(orientation, self,
                                   decimals=self._decimals)

        self.slider.setRange(*self.bounds)
        self.slider.setValue(self.init_value)
        self.slider.valueChangedByHand.connect(
            lambda *x: self.valueChanged.emit(self.slider.value()))
        self.editValue = QLineEdit(self._get_str_value())
        self.editValue.setMaximumWidth(self._EditMaximumWidth)
        self.editValue.setStyleSheet('QLineEdit {  border: none; }')
        self.label = QLabel(self.name)
        self.slider.valueChanged.connect(self._update_label_text)

        if not self._decimals:
            self.editValue.setValidator(QIntValidator(*self.bounds))

        self.slider.valueChangedByHand.connect(
            lambda _: self.editValue.setText(self._get_str_value()))
        self.editValue.editingFinished.connect(self._set_slider_value)

        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(self.editValue)

        self.setFixedHeight(self._Height)
        min_width = self.fontMetrics().width(
            ' = '.join([self.name, self._get_str_value()])) + self._padding
        self.setMinimumWidth(min_width)

    def _set_slider_value(self):
        value = self.editValue.text()
        try:
            if self._decimals:
                value = float(value)
            else:
                value = int(value)
            self.slider.setValue(value)
            if value < self.bounds[0] or value > self.bounds[1]:
                raise ValueError()
        except ValueError:
            self.editValue.setText(self._get_str_value())
            color_animation(self.editValue)
        self.valueChanged.emit(self.slider.value())


class ControlSlider(AnimatedSlider):
    def __init__(self, *args, **kwargs):
        AnimatedSlider.__init__(self, *args, **kwargs)
        self._fixed = False

    def set_fixed(self):
        self.hide_and_show('hide')
        self._fixed = True
        self.context_menu_enabled = False
        self.label.setStyleSheet('QLabel {color: green; }')

    def set_unfixed(self):
        self._fixed = False
        self.context_menu_enabled = True
        self.label.setStyleSheet('QLabel {color: black; }')

    def on_clicked(self):
        if not self._fixed:
            AnimatedSlider.on_clicked(self)


class InfoButton(RoundedPushButton):
    def __init__(self, info, parent=None):
        RoundedPushButton.__init__(self, parent, icon=Icon('info'))
        self.setToolTip(info)


class AbstractInputParametersWidget(QWidget):
    class InputParameters(NamedTuple):
        name: str
        label: str
        type: type
        info: str = None
        none: str = False

    @property
    @abstractmethod
    def PARAMETER_TYPES(self):
        pass

    @property
    @abstractmethod
    def NAME(self):
        pass

    def __init__(self, parent=None):
        super(AbstractInputParametersWidget, self).__init__(parent)
        self.setWindowIcon(Icon('setup'))
        self.setWindowTitle(self.NAME)
        self.default_dict = self.dict_from_config()

    def get_parameters_dict(self):
        parameters_dict = dict()
        for p in self.PARAMETER_TYPES:
            value = getattr(self, p.name)
            if not p.none and value is None:
                return
            parameters_dict[p.name] = value
        return parameters_dict

    def dict_from_config(self):
        return read_config(self.NAME)

    def save_to_config(self, parameters_dict: dict):
        save_config(self.NAME, parameters_dict)

    def _get_layout(self,
                    input_parameter: 'InputParameters'):
        current_value = self.default_dict.get(input_parameter.name, '')
        if current_value is None:
            current_value = ''
        label_widget = QLabel(input_parameter.label)
        input_widget = QLineEdit(str(current_value))
        if input_parameter.type is int:
            input_widget.setValidator(QIntValidator())
        layout = QHBoxLayout()
        layout.addWidget(label_widget, Qt.AlignHCenter)
        layout.addWidget(input_widget, Qt.AlignHCenter)
        if input_parameter.info:
            info_button = InfoButton(input_parameter.info)
            layout.addWidget(info_button, Qt.AlignLeft)

        def get_input(s):
            return validate_scientific_value(input_widget, input_parameter.type, input_parameter.none)

        setattr(AbstractInputParametersWidget, input_parameter.name,
                property(get_input))
        return layout


class BasicInputParametersWidget(AbstractInputParametersWidget):
    apply_signal = pyqtSignal(dict)
    close_signal = pyqtSignal()

    def __init__(self, parent=None):
        AbstractInputParametersWidget.__init__(self, parent)
        self.form = QFormLayout()
        for p in self.PARAMETER_TYPES:
            self.form.addRow(self._get_layout(p))
        self.save_button = self.__init_save_button__()
        self.apply_button = self.__init_apply_button__()
        self.cancel_button = self.__init_cancel_button__()
        self.form.addWidget(self.save_button)
        self.form.addWidget(self.apply_button)
        self.form.addWidget(self.cancel_button)
        self.setLayout(self.form)
        center_widget(self)

    def __init_apply_button__(self):
        apply_button = QPushButton('Apply')

        apply_button.clicked.connect(self.on_apply)
        return apply_button

    def __init_cancel_button__(self):
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.close)
        return cancel_button

    def on_apply(self, *args):
        parameters_dict = self.get_parameters_dict()
        if parameters_dict is not None:
            self.apply_signal.emit(parameters_dict)
            logger.debug(parameters_dict)
            if self.save_button.isChecked():
                self.save_to_config(parameters_dict)
            self.close()

    def close(self):
        self.close_signal.emit()
        AbstractInputParametersWidget.close(self)

    @staticmethod
    def __init_save_button__():
        save_button = QRadioButton('Save parameters')
        save_button.setChecked(True)
        return save_button
