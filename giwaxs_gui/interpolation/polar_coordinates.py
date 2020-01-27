# -*- coding: utf-8 -*-
import logging

import numpy as np
from scipy.ndimage import gaussian_filter1d

from .cpp_box_interpolation import cpp_box_interpolation

logger = logging.getLogger(__name__)


def convert_image(image, r, phi,
                  r_size: int = 512,
                  phi_size: int = 512,
                  r_window: float = 0.5,
                  phi_window: float = 0.5):
    logger.debug(f'image shape = {image.shape}')
    r_step = r.max() / r_size
    phi_step = (phi.max() - phi.min()) / phi_size
    image_vector = image.flatten()
    rr_vector = r.flatten()
    pp_vector = phi.flatten()
    converted_image_ = cpp_box_interpolation(image_vector, rr_vector, pp_vector,
                                             0, r_step, r_size, r_window,
                                             phi.min(), phi_step, phi_size, phi_window)
    converted_image_ /= converted_image_.max()
    return converted_image_


def get_radial_profile(img, r, sigma: float = 0):
    assert img.shape == r.shape
    r = r.astype(np.int)

    tbin = np.bincount(r.ravel(), img.ravel())
    nr = np.bincount(r.ravel())
    radial_profile = np.nan_to_num(tbin / nr)
    if sigma:
        radial_profile = gaussian_filter1d(radial_profile, sigma)
    return radial_profile

