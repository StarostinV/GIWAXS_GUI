# -*- coding: utf-8 -*-

import logging

from pathlib import Path

import h5py

from PyQt5.QtWidgets import (QTreeView, QFileDialog, QWidget,
                             QHBoxLayout, QLabel, QMenu)
from PyQt5.QtCore import Qt, QItemSelectionModel
from PyQt5.QtGui import QStandardItem, QStandardItemModel

from .utils import read_h5_dict
from .items import (file_item_factory, FolderGroupItem, RoiItem,
                    H5GiwaxsItem, H5FileItem, AbstractGroupItem,
                    AbstractFileItem, H5DatasetItem)

from ..basic_widgets import RoundedPushButton
from ..roi.roi_widgets import EmptyROI, FileWidgetRoi
from ..roi.roi_containers import BasicROIContainer
from ..signal_connection import SignalConnector, SignalContainer, StatusChangedContainer

from ...utils import Icon, RoiParameters, save_execute

logger = logging.getLogger(__name__)


class FileModel(QStandardItemModel):
    def __init__(self):
        super(FileModel, self).__init__()
        self.setHorizontalHeaderLabels([''])
        self.setRowCount(0)

    def add_folder(self, folder_path: Path):
        folder_item = FolderGroupItem(folder_path)
        self.appendRow(folder_item)
        return folder_item

    def add_file(self, filepath: Path, row: int = None):
        item = file_item_factory(filepath)
        if item:
            if row is None:
                self.appendRow(item)
            else:
                self.insertRow(row, item)

        return item


class FileWidget(BasicROIContainer, QTreeView):
    def __init__(self, signal_connector: SignalConnector, parent=None):
        BasicROIContainer.__init__(self, signal_connector)
        QTreeView.__init__(self, parent=parent)
        self._model = FileModel()
        self.setEditTriggers(QTreeView.NoEditTriggers)
        self.setModel(self._model)
        self.selectionModel().currentChanged.connect(self._on_clicked)
        # self.clicked.connect(self._on_clicked)
        self.current_dataset = None
        self._future_dataset = None
        self.customContextMenuRequested.connect(
            self.context_menu
        )
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.__init_ui__()
        self.show()

    def __init_ui__(self):

        add_file_button = RoundedPushButton(icon=Icon('data'), radius=30,
                                            background_color='transparent')
        add_file_button.clicked.connect(self._open_add_file_menu)
        add_folder_button = RoundedPushButton(icon=Icon('folder'), radius=30,
                                              background_color='transparent')
        add_folder_button.clicked.connect(self._open_add_folder_menu)
        layout = self._get_header_layout(QStandardItem(), 'Files')
        layout.addWidget(add_file_button)
        layout.addWidget(add_folder_button)

    @save_execute('File widget process signal failed.')
    def process_signal(self, s: SignalContainer):
        super().process_signal(s)
        if self.current_dataset:
            for _ in s.geometry_changed():
                self.current_dataset.properties_item.update(
                    beam_center=self.image.beam_center
                )
            for _ in s.intensity_limits_changed():
                self.current_dataset.properties_item.update(
                    intensity_limits=self.image.intensity_limits
                )
            for _ in s.transformation_added():
                self.current_dataset.properties_item.update(
                    transformations=self.image.transformation.transformation_list
                )
            for _ in s.scale_changed():
                self.current_dataset.properties_item.update(
                    scale=self.image.scale
                )

    def add_roi(self, params: RoiParameters):
        roi = self._get_roi(params)
        if roi:
            roi.value_changed.connect(
                lambda value: self.signal_connector.emit_upward(
                    SignalContainer().segment_moved(value)))
            roi.status_changed.connect(self.emit_status_changed)
            roi.arbitrary_signal.connect(self.signal_connector.emit_upward)
            if not self._future_dataset:
                self.roi_dict[params.key] = roi
            self._add_item(roi)
            return roi

    def _get_roi(self, params: RoiParameters) -> 'AbstractROI':
        if self.current_dataset or self._future_dataset:
            return FileWidgetRoi(params)
        else:
            return EmptyROI(params)

    def _add_item(self, roi: FileWidgetRoi or EmptyROI):
        if ((self.current_dataset or self._future_dataset) and
                isinstance(roi, FileWidgetRoi)):
            item = RoiItem(roi.value.name)
            roi.set_item(item)
            parent = self._future_dataset or self.current_dataset
            parent.appendRow(item)
            # self.setExpanded(parent.index(), True)
            return roi

    def _remove_item(self, roi: FileWidgetRoi or EmptyROI):
        if self.current_dataset and isinstance(roi, FileWidgetRoi):
            self.current_dataset.removeRow(roi.item.row())

    def _on_status_changed(self, sig: StatusChangedContainer):
        if self.current_dataset:
            if not sig.status:
                for k in sig.keys:
                    self.roi_dict[k].set_inactive()
                    self.selectionModel().select(
                        self.roi_dict[k].item.index(),
                        QItemSelectionModel.Deselect)
            else:
                for k in sig.keys:
                    self.roi_dict[k].set_active()
                    self.selectionModel().select(
                        self.roi_dict[k].item.index(),
                        QItemSelectionModel.Select)

    def _open_add_file_menu(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self, 'Open image', '',
            'edf, tiff, h5, hdf5 files (*.tiff *.edf *.h5 *.hdf5)', options=options)
        if filepath:
            self._model.add_file(Path(filepath))

    def _open_add_folder_menu(self):
        options = QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        folder_path = QFileDialog.getExistingDirectory(
            self, 'Choose directory containing edf, tiff or h5 files', '',
            options=options)
        if folder_path:
            self._model.add_folder(Path(folder_path))

    def _get_header_layout(self, item: QStandardItem, label: str):
        header_widget = QWidget(self)
        layout = QHBoxLayout()
        header_widget.setLayout(layout)
        label_widget = QLabel(label)
        layout.addWidget(label_widget, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        self._model.appendRow(item)
        self.setIndexWidget(item.index(), header_widget)
        return layout

    def _on_clicked(self, index):
        item = self._model.itemFromIndex(index)
        if isinstance(item, AbstractGroupItem) and not item.content_uploaded:
            item.update_content()
            self.setExpanded(item.index(), True)
        elif isinstance(item, AbstractFileItem):
            if item.should_parse_file:
                self._parse_h5_item(item)
            else:
                data = item.get_data()
                if self.current_dataset != item and data.ndim == 2:
                    self._change_image_item(item, data)
        elif (isinstance(item, RoiItem) and
              item.roi and item.parent() is self.current_dataset):
            item.roi.send_active()

    @save_execute('Could not read saved h5 image.', silent=False)
    def _parse_h5_item(self, item: H5GiwaxsItem):
        try:
            self._future_dataset = item
            key = item.h5_key
            with h5py.File(item.filepath, 'r') as f:
                group = f[key]
                if 'image' not in group.keys():
                    return
                data = group['image'][()]
                if data.ndim != 2:
                    return
                item.properties_item.update(**read_h5_dict(group.attrs))
                roi_key = 0
                for k in group.keys():
                    dset = group[k]
                    if 'radius' in dset.attrs.keys() and 'width' in dset.attrs.keys():
                        params_dict = read_h5_dict(dset.attrs)
                        params = RoiParameters(**params_dict, key=roi_key)
                        self.add_roi(params)
                        roi_key += 1
        finally:
            self._future_dataset = None
            item.should_parse_file = False
        self._change_image_item(item, data)

    def _change_image_item(self, item, data):
        self.image.set_image(data)
        sc_delete = SignalContainer(app_node=self)
        sc_create = SignalContainer(app_node=self)
        sc_create.geometry_changed(0)
        sc_create.image_changed(0)
        for roi in self.roi_dict.values():
            roi.set_inactive()
            sc_delete.segment_deleted(
                roi.value, signal_type=SignalContainer.SignalTypes.except_for_names)
        self.roi_dict = dict()
        self.current_dataset = item
        for child_item in self.current_dataset.get_child_rois():
            value = child_item.roi.value
            self.roi_dict[value.key] = child_item.roi
            sc_create.segment_created(
                value, signal_type=SignalContainer.SignalTypes.except_for_names)
        if self.current_dataset.has_properties:
            self._set_file_properties_to_image()
        else:
            self._set_init_properties_to_file()

        sc_delete.send()
        sc_create.send()

    def _set_file_properties_to_image(self):
        properties = self.current_dataset.properties_item.get_dict()
        if 'intensity_limits' in properties.keys():
            self.image.set_image_limits(properties['intensity_limits'])
        if 'beam_center' in properties.keys():
            self.image.set_beam_center(properties['beam_center'])
        if 'transformations' in properties.keys():
            for name in properties['transformations']:
                self.image.add_transformation(name)
        if 'scale' in properties.keys():
            self.image.set_scale(properties['scale'])

    def _set_init_properties_to_file(self):
        self.current_dataset.properties_item.update(
            beam_center=self.image.beam_center,
            transformations=self.image.transformation.transformation_list,
            intensity_limits=self.image.intensity_limits,
            scale=self.image.scale
        )

    def context_menu(self, position):
        item = self._model.itemFromIndex(self.indexAt(position))
        menu = QMenu()
        if isinstance(item, FolderGroupItem):
            update_folder = menu.addAction('Update folder')
            update_folder.triggered.connect(lambda: self.update_group(item))
            close_folder = menu.addAction('Close folder')
            close_folder.triggered.connect(lambda: self._on_closing_group(item))
        elif isinstance(item, H5FileItem):
            update_folder = menu.addAction('Update h5 file')
            update_folder.triggered.connect(lambda: self.update_group(item))
            close_folder = menu.addAction('Close h5 file')
            close_folder.triggered.connect(lambda: self._on_closing_group(item))
        elif isinstance(item, AbstractFileItem):
            save_menu = menu.addMenu('Save')
            save_as_h5 = save_menu.addAction('Save as h5 file')
            save_to_h5 = save_menu.addAction('Save to existing h5 file')
            save_as_h5.triggered.connect(item.save_as_h5)
            save_to_h5.triggered.connect(item.save_to_h5)
            if isinstance(item, H5DatasetItem):
                save_here = save_menu.addAction('Save to current h5 file')
                save_here.triggered.connect(item.save_here)
        else:
            return
        menu.exec_(self.viewport().mapToGlobal(position))

    def _on_closing_group(self, item: H5FileItem or FolderGroupItem):
        if self._group_contains_current_dataset(item):
            self.current_dataset = None
            for k, v in self.roi_dict.items():
                self.roi_dict[k] = EmptyROI(v.value)
        item.close()

    def _group_contains_current_dataset(self, item: H5FileItem or FolderGroupItem):
        return (
                self.current_dataset and
                (isinstance(item, H5FileItem) and
                 item.filepath == self.current_dataset.filepath
                 or
                 isinstance(item, FolderGroupItem) and
                 item.filepath in self.current_dataset.filepath.parents)
        )

    @save_execute('Error occured while trying to update folder.', silent=False)
    def update_group(self, item: H5FileItem or FolderGroupItem):
        if self._group_contains_current_dataset(item):
            self.current_dataset = None
            for k, v in self.roi_dict.items():
                self.roi_dict[k] = EmptyROI(v.value)
        item.removeRows(0, item.rowCount())
        item.update_content()
        self.setExpanded(item.index(), True)
