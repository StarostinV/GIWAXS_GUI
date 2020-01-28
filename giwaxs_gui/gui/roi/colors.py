# -*- coding: utf-8 -*-

from PyQt5.QtGui import QColor

# TODO: wrap into class (save config to json) and provide option for customization and changing colors


COLOR_DICT = dict(
    active=QColor(255, 139, 66, 70), active_bright=QColor(255, 139, 66),
    inactive=QColor(0, 0, 255, 50), inactive_bright=QColor(0, 0, 255),
    fixed=QColor(0, 255, 0, 50), fixed_bright=QColor(0, 255, 0),
    fixed_active=QColor(255, 0, 255, 50), fixed_active_bright=QColor(255, 0, 255)
)

