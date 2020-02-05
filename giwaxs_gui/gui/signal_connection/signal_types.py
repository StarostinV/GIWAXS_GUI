from enum import Enum
from .signal_keys import SignalKeys


class SignalTypes(Enum):
    broadcast = 0
    only_for_names = 1
    except_for_names = 2
    default = 0


_SPECIAL_SIGNAL_TYPES = {
    SignalKeys.name_changed: SignalTypes.except_for_names,
    SignalKeys.segment_moved: SignalTypes.except_for_names,
    SignalKeys.geometry_changed: SignalTypes.except_for_names,
    SignalKeys.type_changed: SignalTypes.except_for_names
}


def _get_type_by_key(signal_key: SignalKeys):
    return _SPECIAL_SIGNAL_TYPES.get(signal_key, SignalTypes.default)
