# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import (QSlider, QLineEdit, QHBoxLayout,
                             QLabel, QWidgetAction, QMenu)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt, pyqtSignal

from .buttons import RoundedPushButton

from ...utils import color_animation

logger = logging.getLogger(__name__)


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