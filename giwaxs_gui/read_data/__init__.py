# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Iterable, List

import numpy as np
import cv2

from .read_edf import read_edf_from_file

_PROJECT_DIR = Path(__file__).parents[1]

_TIFF_PATHS = list(_PROJECT_DIR.rglob('*.tiff'))
_EDF_PATHS = list(_PROJECT_DIR.rglob('*.edf'))


def get_image(num: int = 0, *, random: bool = False,
              normalize: bool = True) -> np.array:
    if random:
        filepath = np.random.choice(_TIFF_PATHS, 1)[0]
    else:
        try:
            filepath = _TIFF_PATHS[num]
        except IndexError:
            raise FileNotFoundError()
    return get_image_from_path(filepath, normalize=normalize)


def get_images(nums: Iterable or int, normalize: bool = True) -> List[np.array]:
    if isinstance(nums, int):
        image_paths = np.random.choice(_TIFF_PATHS, nums, replace=False)
    else:
        image_paths = [_TIFF_PATHS[n] for n in nums]
    return [get_image_from_path(path, normalize) for path in image_paths]


def get_image_from_path(filepath, normalize: bool = True) -> np.array:
    filepath = str(filepath)
    if filepath.endswith('.edf'):
        image = read_edf_from_file(filepath)[0]
    else:
        image = np.flip(cv2.imread(filepath, cv2.IMREAD_GRAYSCALE), 0)
    if normalize:
        image = normalize_image(image)
    return image


def get_raw_image(num: int = 0, *, random: bool = False):
    if random:
        num = np.random.choice(list(range(len(_EDF_PATHS))), 1)[0]
    try:
        return read_edf_from_file(str(_EDF_PATHS[num]))[0]
    except IndexError:
        raise FileNotFoundError()


def normalize_image(image: np.ndarray):
    # TODO: move to a standalone optional functionality with parameter sigma_factor
    # ( hidden vertical slider on the widget on the right ? )
    m, s = image.mean(), image.std() * 2
    image = np.clip(image, m - s, m + s)
    image = (image - image.min()) / image.max()
    return image

