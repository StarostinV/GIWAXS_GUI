# -*- coding: utf-8 -*-
import weakref
from abc import abstractmethod
from typing import Union

from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QMenu, QWidgetAction, QLineEdit

from ..signal_connection import SignalContainer
from ...utils import RoiParameters


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