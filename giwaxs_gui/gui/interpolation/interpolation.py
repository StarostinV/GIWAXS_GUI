import logging
from typing import NamedTuple

import numpy as np
import cv2

from .modes import get_mode
from .parameters_widget import get_interpolation_parameters

logger = logging.getLogger(__name__)


class Interpolation(object):
    """
    This class is a singleton and it contains main functionality needed for 2d polar interpolation.
    Its instance is held by ..global_context.Image class so that other widgets could
    get access to it (for instance, for fast angular profile calculation).
    """

    def __init__(self):
        self._interpolation_geometry = None
        self._image = None
        params = get_interpolation_parameters()
        self._r_size = params.get('r_size', None)
        self._phi_size = params.get('phi_size', None)
        mode_name = params.get('mode', '')
        self._algorithm = get_mode(mode_name)

    @property
    def interpolation_geometry(self) -> 'InterpolationGeometry' or None:
        return self._interpolation_geometry

    @property
    def image(self) -> np.ndarray or None:
        return self._image

    @property
    def r_size(self):
        return self._r_size

    @property
    def phi_size(self):
        return self._phi_size

    @property
    def algorithm_flag(self) -> int:
        return self._algorithm.flag

    @property
    def algorithm_name(self) -> str:
        return self._algorithm.name

    @property
    def r_axis(self) -> np.ndarray or None:
        try:
            return self._interpolation_geometry.r
        except AttributeError:  # should be faster than checking if not None
            return

    @property
    def phi_axis(self) -> np.ndarray or None:
        try:
            return self._interpolation_geometry.p
        except AttributeError:
            return

    def set_algorithm(self, mode: 'Mode' or str):
        if isinstance(mode, str):
            mode = get_mode(mode)
        if not mode:
            return
        self._algorithm = mode

    def set_geometry(self, geometry: 'Geometry', r_size: int = None, phi_size: int = None):
        self.set_shape(r_size, phi_size)
        self._interpolation_geometry = InterpolationGeometry.get(
            geometry, self._r_size, self._phi_size)

    def set_shape(self, r_size: int = None, phi_size: int = None):
        if r_size:  # anyway should be nonzero
            self._r_size = r_size
        if phi_size:
            self._phi_size = phi_size

    def set_parameters(self, parameters: dict):
        self.set_shape(parameters.get('r_size', None), parameters.get('phi_size', None))
        self.set_algorithm(parameters.get('mode', None))

    def interpolate(self, image: np.ndarray) -> np.ndarray or None:
        if any(x is None for x in (self.interpolation_geometry, image)):
            return
        xx = self.interpolation_geometry.xx.astype(np.float32)
        yy = self.interpolation_geometry.yy.astype(np.float32)
        try:
            logger.info(f'Calculating interpolation.')
            self._image = cv2.remap(image.astype(np.float32), xx, yy,
                                    interpolation=self.algorithm_flag)
            logger.info(f'Interpolation is calculated.')
            return self._image
        except cv2.error as err:
            logger.exception(err)
            return


class InterpolationGeometry(NamedTuple):
    """
    Interpolation geometry container used for polar interpolation.
    Should only be initialized by the class method '.get()'.
    Fields:
        r: np.ndarray - 1d radius axis for interpolated image
        p: np.ndarray - 1d angular axis [rad] for interpolated image
        xx: np.ndarray - 2d map1 for cv2 remap function
        yy: np.ndarray - 2d map2 for cv2 remap function
    """
    r: np.ndarray
    p: np.ndarray
    xx: np.ndarray
    yy: np.ndarray

    @classmethod
    def get(cls, geometry: 'Geometry', r_size: int, phi_size: int):
        rr = geometry.rr
        phi = geometry.phi
        center = geometry.beam_center
        if any(x is None for x in (rr, phi, center, r_size, phi_size)):
            return
        r = np.linspace(rr.min(), rr.max(), r_size)
        r_matrix = r[np.newaxis, :].repeat(phi_size, axis=0)
        p = np.linspace(phi.min(), phi.max(), phi_size)
        p_matrix = p[:, np.newaxis].repeat(r_size, axis=1)
        xx = r_matrix * np.cos(p_matrix) + center[1]
        yy = r_matrix * np.sin(p_matrix) + center[0]
        return cls(r=r, p=p, xx=xx, yy=yy)
