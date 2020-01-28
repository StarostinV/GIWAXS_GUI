# -*- coding: utf-8 -*-
import logging
from abc import abstractmethod
from copy import deepcopy
from pathlib import Path

import numpy as np
import h5py

from PyQt5.QtGui import QStandardItem

from .utils import (save_as_h5_dialog, save_to_h5_dialog,
                    save_create_h5_subgroup,
                    prepare_dict_to_h5, parse_h5_group,
                    filter_dirs, filter_files)
from ...read_data import get_image_from_path
from ...utils import Icon, save_execute

logger = logging.getLogger(__name__)

_H5_GIWAXS_DATA_KEY = '__GIWAXS_DATA__'


class AbstractItem(QStandardItem):
    def __init__(self, filepath: Path, *args, **kwargs):
        self.filepath = filepath
        super().__init__(self.__get_name__())

    def __get_name__(self):
        return self.filepath.name


class AbstractFileItem(AbstractItem):
    should_parse_file = False

    @property
    def properties_item(self):
        if not self._properties_item:
            self._properties_item = PropertiesItem('Properties')
            self.insertRow(0, self.properties_item)
        return self._properties_item

    @property
    def has_properties(self):
        return self._properties_item is not None

    def __init__(self, filepath: Path, *args, **kwargs):
        super().__init__(filepath)
        self._properties = dict()
        self._properties_item = None
        self.setIcon(Icon('data'))

    def get_child_rois(self):
        for row in range(self.rowCount()):
            item = self.child(row)
            if isinstance(item, RoiItem) and item.roi:
                yield item

    @abstractmethod
    def get_data(self) -> np.array:
        pass

    @save_execute('An error occured while trying to save file.',
                  silent=False, error_title='Save file error')
    def save_as_h5(self, *args):
        filepath = save_as_h5_dialog()
        if filepath:
            with h5py.File(filepath, 'w') as f:
                self._save_to_h5(f)

    @save_execute('An error occured while trying to save file.',
                  silent=False, error_title='Save file error')
    def save_to_h5(self, *args):
        filepath = save_to_h5_dialog()
        if filepath:
            with h5py.File(filepath, 'a') as f:
                self._save_to_h5(f)

    def _save_to_h5(self, f: h5py.File, data: np.ndarray = None, name: str = None):
        if data is None:
            data = self.get_data()
        # TODO: fix problem with saving to h5!
        name = name or self.__get_name__().split('.')[0]
        group = save_create_h5_subgroup(f, name)
        group.attrs.update({_H5_GIWAXS_DATA_KEY: 1})
        group.attrs.update(prepare_dict_to_h5(self.properties_item.get_dict()))
        group.create_dataset('image', data=data)
        for i, item in enumerate(self.get_child_rois()):
            d = prepare_dict_to_h5(item.get_dict())
            dset = save_create_h5_subgroup(group, d.get('name', 'segment'),
                                           data=d.pop('key', 0))
            dset.attrs.update(d)


class AbstractGroupItem(AbstractItem):
    def __init__(self, filepath: Path, *args, **kwargs):
        super(AbstractGroupItem, self).__init__(filepath)
        self.setIcon(Icon('folder'))
        self.content_uploaded = False

    def update_content(self):
        self.content_uploaded = True
        return self._update_content()

    @abstractmethod
    def _update_content(self):
        pass


class AttributesItem(QStandardItem):
    @abstractmethod
    def get_dict(self):
        pass


class RoiItem(AttributesItem):
    def __init__(self, name: str):
        self.roi = None
        QStandardItem.__init__(self, name)
        self.setIcon(Icon('roi_item'))

    def get_dict(self):
        if not self.roi:
            return dict()
        else:
            return self.roi.value._asdict()


class PropertiesItem(AttributesItem):
    def __init__(self, *args):
        super().__init__(*args)
        self._properties = dict()
        self.setIcon(Icon('properties'))

    def update(self, **kwargs):
        self._properties.update(kwargs)

    def get_dict(self):
        return deepcopy(self._properties)


class H5Item(AbstractItem):
    def __init__(self, filepath: Path, h5_key: str, *args, **kwargs):
        self.h5_key = h5_key
        super(H5Item, self).__init__(filepath)

    def __get_name__(self):
        return self.h5_key.split('/')[-1]


class H5GroupItem(H5Item, AbstractGroupItem):
    def __init__(self, filepath: Path, h5_key: str, *args, **kwargs):
        kwargs['filepath'] = filepath
        kwargs['h5_key'] = h5_key
        super(H5GroupItem, self).__init__(*args, **kwargs)
        self.setIcon(Icon('h5_group_folder'))
        # H5Item.__init__(self, filepath, h5_key)

    @save_execute('Could not read h5 file.', silent=False)
    def _update_content(self):
        with h5py.File(self.filepath, 'r') as f:
            for h5item in parse_h5_group(f, self.h5_key):
                item = h5_item_factory(h5item, self.filepath)
                if item:
                    self.appendRow(item)


class H5FileItem(H5GroupItem):
    def __init__(self, filepath: Path, *args, **kwargs):
        kwargs['filepath'] = filepath
        kwargs['h5_key'] = ''
        super(H5FileItem, self).__init__(*args, **kwargs)
        self.setIcon(Icon('h5_folder'))

    def __get_name__(self):
        return self.filepath.name

    def close(self):
        parent = self.parent() or self.model()
        parent.removeRow(self.row())


class H5DatasetItem(H5Item, AbstractFileItem):
    @save_execute('Error while trying to get data from h5 file.', silent=True)
    def get_data(self):
        with h5py.File(self.filepath) as f:
            return f[self.h5_key][()]

    def save_here(self):
        with h5py.File(self.filepath) as f:
            data = self.get_data()
            name = self.text()
            del f[self.h5_key]
            # with h5py.File(self.filepath) as f:
            self._save_to_h5(f, data, name)


class H5GiwaxsItem(H5DatasetItem):
    should_parse_file = True

    @save_execute('Error while trying to get data from h5 file.', silent=True)
    def get_data(self):
        with h5py.File(self.filepath, 'r') as f:
            return f[f'{self.h5_key}/image'][()]


class FolderGroupItem(AbstractGroupItem):
    def _update_content(self):
        for dirpath in filter_dirs(self.filepath):
            self.appendRow(FolderGroupItem(dirpath))
        for filepath in filter_files(self.filepath):
            item = file_item_factory(filepath)
            if item:
                self.appendRow(item)

    def close(self):
        parent = self.parent() or self.model()
        parent.removeRow(self.row())


class EdfFileItem(AbstractFileItem):
    @save_execute('Cound not read from edf file', silent=False)
    def get_data(self):
        return get_image_from_path(self.filepath)


class TiffFileItem(AbstractFileItem):
    @save_execute('Cound not read from tiff file', silent=False)
    def get_data(self):
        return get_image_from_path(self.filepath)


def file_item_factory(filepath: Path):
    if filepath.suffix == '.edf':
        return EdfFileItem(filepath)
    elif filepath.suffix in ['.tif', '.tiff']:
        return TiffFileItem(filepath)
    elif filepath.suffix == '.h5':
        return H5FileItem(filepath)


def h5_item_factory(h5item: h5py.Group or h5py.Dataset, filepath: Path):
    if isinstance(h5item, h5py.Group):
        if _H5_GIWAXS_DATA_KEY in h5item.attrs.keys():
            return H5GiwaxsItem(filepath, h5item.name)
        else:
            return H5GroupItem(filepath, h5item.name)
    elif isinstance(h5item, h5py.Dataset):
        return H5DatasetItem(filepath, h5item.name)
