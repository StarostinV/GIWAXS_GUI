from typing import NamedTuple
import logging

import numpy as np

from giwaxs_gui.gui.exceptions import UnknownTransformation

logger = logging.getLogger(__name__)


class Geometry(NamedTuple):
    xx: np.ndarray = None
    yy: np.ndarray = None
    rr: np.ndarray = None
    phi: np.ndarray = None
    beam_center: tuple = None


class ImageScale(NamedTuple):
    scale: float = 1.
    unit: str = ''
    previous_scale: float = 1.


class RingAngles(NamedTuple):
    angle: float = None
    angle_std: float = None


class ImageTransformation(object):
    @property
    def transformation_list(self):
        return self._transformation_list

    def __init__(self):
        self._transformation_list = list()
        self._transformation_dict = dict(
            horizontal=self.horizontal,
            vertical=self.vertical,
            rotate_right=self.rotate_right,
            rotate_left=self.rotate_left)

    def add_transformation(self, name: str):
        if name not in self._transformation_dict.keys():
            raise UnknownTransformation()
        self._transformation_list.append(name)
        # TODO: clever search, delete opposite transformations

    def transform(self, image):
        for t in self._transformation_list:
            image = self._transformation_dict[t](image)
        return image

    def last_transform(self, image):
        if self._transformation_list:
            return self._transformation_dict[self._transformation_list[-1]](image)
        else:
            return image

    def clear(self):
        self._transformation_list = list()

    @staticmethod
    def horizontal(image):
        return np.flip(image, axis=1)

    @staticmethod
    def vertical(image):
        return np.flip(image, axis=0)

    @staticmethod
    def rotate_right(image):
        return np.rot90(image, k=-1)

    @staticmethod
    def rotate_left(image):
        return np.rot90(image, k=1)


class Image(object):
    @property
    def image(self):
        return self._image

    @property
    def shape(self):
        return self._image.shape if self._image is not None else None

    @property
    def geometry(self):
        return self._geometry

    @property
    def beam_center(self):
        return self._beam_center

    @property
    def rr(self):
        return self.geometry.rr

    @property
    def phi(self):
        return self.geometry.phi

    @property
    def xx(self):
        return self.geometry.xx

    @property
    def yy(self):
        return self.geometry.yy

    @property
    def intensity_limits(self):
        return self._intensity_limits

    @property
    def scale(self):
        return self._scale.scale

    @property
    def scale_unit(self):
        return self._scale.unit

    @property
    def scale_change(self):
        return self.scale / self._scale.previous_scale

    @property
    def ring_angle(self):
        return self._ring_angles.angle

    @property
    def ring_angle_str(self):
        return self._ring_angles.angle_std

    def __init__(self):
        self._source_image = None
        self._image = None
        self.transformation = ImageTransformation()
        self._intensity_limits = None
        self._keep_limits = True
        self.save_transformation = False
        self._beam_center = (0, 0)
        self._geometry = Geometry()
        self._scale = ImageScale()
        self._ring_angles = RingAngles()

    def set_image_limits(self, limits: tuple = None):
        self._intensity_limits = limits
        if not limits:
            self._keep_limits = False
        else:
            self._keep_limits = True

    def set_beam_center(self, beam_center: tuple):
        if beam_center:
            self._beam_center = beam_center
            self.update_geometry()

    def add_transformation(self, name):
        if self._image is None:
            return
        try:
            self.transformation.add_transformation(name)
        except UnknownTransformation:
            logger.exception('')
            return
        self._image = self.transformation.last_transform(self._image)
        self.update_geometry()

    def set_image(self, image):
        if not isinstance(image, np.ndarray) or image.ndim != 2:
            logger.error(f'Set image got wrong argument: {image}')
            return
        if not self.save_transformation:
            self.transformation.clear()
        if not self._keep_limits:
            self._intensity_limits = None
        self._source_image = image
        self._image = self.transformation.transform(image)
        self.update_geometry()

    def update_geometry(self):
        if self._image is None or self._beam_center is None:
            return
        xx, yy = np.meshgrid(
            np.arange(self._image.shape[1]) - self._beam_center[1],
            np.arange(self._image.shape[0]) - self._beam_center[0]
        )
        rr = np.sqrt(xx ** 2 + yy ** 2)
        phi = np.arctan2(yy, xx)
        self._geometry = Geometry(xx, yy, rr, phi, self._beam_center)
        self._ring_angles = RingAngles(
            angle=(phi.max() + phi.min()) / 2 * 180 / np.pi,
            angle_std=(phi.max() - phi.min()) * 180 / np.pi
        )

    def set_scale(self, scale: float, unit: str = ''):
        self._scale = ImageScale(scale, unit, self.scale)
