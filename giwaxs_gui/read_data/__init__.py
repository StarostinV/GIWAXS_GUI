# -*- coding: utf-8 -*-

import numpy as np
import cv2

from .read_edf import read_edf_from_file


def get_image_from_path(filepath) -> np.array:
    filepath = str(filepath)
    if filepath.endswith('.edf'):
        image = read_edf_from_file(filepath)[0]
    else:
        image = np.flip(cv2.imread(filepath, cv2.IMREAD_GRAYSCALE), 0)
    return image
