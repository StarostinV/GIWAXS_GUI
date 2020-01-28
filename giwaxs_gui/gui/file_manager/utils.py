# -*- coding: utf-8 -*-

import logging
from pathlib import Path

import numpy as np
import h5py

from PyQt5.QtWidgets import QFileDialog

logger = logging.getLogger(__name__)

_AVAILABLE_FILE_FORMATS = tuple('.tif .tiff .h5 .hdf5 .edf'.split())


def filter_files(path: Path):
    yield from (p for p in path.iterdir() if p.suffix in _AVAILABLE_FILE_FORMATS)


def filter_dirs(path: Path):
    yield from (p for p in path.iterdir() if p.is_dir())


def parse_h5_group(file: h5py.File, key: str):
    group = file[key] if key else file
    yield from (group[k] for k in group.keys())


def save_as_h5_dialog():
    return QFileDialog.getSaveFileName(None, 'Create h5 file', '', 'hdf5 files (*.h5)')[0]


def save_to_h5_dialog():
    options = QFileDialog.Options()
    options |= QFileDialog.DontUseNativeDialog
    filename, _ = QFileDialog.getOpenFileName(
        None, 'Choose h5 file', '',
        'hdf5 files (*.h5)', options=options)
    return filename


def save_create_h5_subgroup(group: h5py.Group, name: str, data=None):
    init_name = name
    i = 1
    while name in group.keys():
        name = f'{init_name}_{i}'
        i += 1
    if data is not None:
        return group.create_dataset(name, data=data)
    else:
        return group.create_group(name)


def prepare_dict_to_h5(d: dict):
    d = dict(d)
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = v.encode()
        elif v is None:
            d[k] = 'none'.encode()
        elif isinstance(v, list) or isinstance(v, tuple):
            d[k] = [item.encode() if isinstance(item, str) else item
                    for item in v if item is not None]
    return d


def read_h5_dict(d):
    d = dict(d)
    for k, v in d.items():
        if isinstance(v, bytes):
            if v == b'none':
                d[k] = None
            else:
                d[k] = v.decode()
        elif isinstance(v, np.ndarray):
            d[k] = [item.decode() if isinstance(item, bytes) else item
                    for item in v]
    return d