from typing import NamedTuple
from traceback import print_stack
import logging

import cv2

logger = logging.getLogger(__name__)


class _Mode(NamedTuple):
    name: str
    flag: int


INTERPOLATION_MODES = (
    _Mode('Nearest', cv2.INTER_NEAREST),
    _Mode('Bilinear', cv2.INTER_LINEAR),
    _Mode('Cubic', cv2.INTER_CUBIC),
    _Mode('Lanczos', cv2.INTER_LANCZOS4)
)


def get_mode(mode_name: str):
    # maybe a frozen dict would be a better solution, but it requires
    # additional dependencies
    for m in INTERPOLATION_MODES:
        if m.name == mode_name:
            return m
    else:
        logger.error(f'Unknown mode name {mode_name}. Traceback: \n {print_stack(limit=4)}')
        return INTERPOLATION_MODES[0]  # only for unexpected errors
