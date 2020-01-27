import logging
from functools import wraps
from typing import NamedTuple
from pathlib import Path
from enum import Enum

from PyQt5.QtWidgets import (QGraphicsColorizeEffect, QLineEdit,
                             QWidget, QApplication, QMessageBox)
from PyQt5.QtCore import QPropertyAnimation, Qt
from PyQt5.QtGui import QColor, QIcon

ICON_PATH = Path(__file__).parents[0] / 'static' / 'icons'

logger = logging.getLogger(__name__)


class RoiTypes(Enum):
    ring = 1
    segment = 2


class RoiParameters(NamedTuple):
    radius: float
    width: float
    angle: float = 180
    angle_std: float = 360
    orientations: list = None
    key: int = None
    name: str = None
    movable: bool = True
    fitted: bool = False
    fit_r_parameters: tuple = None
    type: str = RoiTypes.ring

    roi_types = RoiTypes  # not a field!


def save_execute(message: str = '', *, errors: tuple = None,
                 silent: bool = True, error_title: str = 'Error'):
    if not errors:
        errors = Exception

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except errors as err:
                logger.exception(f'Error while save_execute of {func.__name__}'
                                 f' with arguments {args}, {kwargs}:\n'
                                 f'{message}:\n{err}')
                if not silent:
                    show_error(message, error_title)

        return wrapper

    return decorator


def show_error(err: str, error_title: str):
    mb = QMessageBox()
    mb.setWindowTitle(error_title)
    logger.info(f'Error message shown: {err}.')
    mb.setWindowIcon(Icon('error'))
    mb.setText(err)
    mb.exec_()


class Icon(QIcon):
    def __init__(self, name: str):
        if name.find('.') == -1:
            name += '.png'
        name = str(ICON_PATH / name)
        QIcon.__init__(self, name)


def center_widget(widget):
    frame_gm = widget.frameGeometry()
    screen = QApplication.desktop().screenNumber(
        QApplication.desktop().cursor().pos())
    center_point = QApplication.desktop().screenGeometry(
        screen).center()
    frame_gm.moveCenter(center_point)
    widget.move(frame_gm.topLeft())


def validate_scientific_value(q_line_edit: QLineEdit,
                              data_type: type or None = float,
                              empty_possible: bool = False,
                              additional_conditions: tuple = ()):
    text_value = q_line_edit.text().replace(',', '.')
    if data_type is None:
        return text_value
    try:
        value = data_type(text_value)
    except ValueError:
        if not empty_possible:
            color_animation(q_line_edit)
        return
    for condition in additional_conditions:
        if not condition(value):
            return
    return value


def color_animation(widget: QWidget, color=Qt.red):
    effect = QGraphicsColorizeEffect(widget)
    widget.setGraphicsEffect(effect)

    widget.animation = QPropertyAnimation(effect, b"color")

    widget.animation.setStartValue(QColor(color))
    widget.animation.setEndValue(QColor(Qt.black))

    widget.animation.setLoopCount(1)
    widget.animation.setDuration(1500)
    widget.animation.start()
