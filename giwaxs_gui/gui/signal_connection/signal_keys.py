from enum import auto

from ...utils import AutoName


class SignalKeys(AutoName):
    # AutoName used for debugging, may be changed to int in the future
    image_changed = auto()
    geometry_changed = auto()
    geometry_changed_finish = auto()
    transformation_added = auto()

    status_changed = auto()
    name_changed = auto()
    scale_changed = auto()
    type_changed = auto()

    segment_created = auto()
    segment_deleted = auto()
    segment_moved = auto()

    segment_fixed = auto()
    segment_unfixed = auto()
    intensity_limits_changed = auto()
