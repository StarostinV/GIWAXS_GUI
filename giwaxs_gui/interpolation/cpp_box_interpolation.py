import ctypes
import platform
from pathlib import Path

import numpy as np

if platform.system() == 'Windows':
    DLL_PATH = Path(__file__).parents[1] / 'static' / 'dll' / 'libboxInterpolation.dll'
elif platform.system() == 'Linux':
    DLL_PATH = Path(__file__).parents[1] / 'static' / 'dll' / 'libboxInterpolation4.so'
    Path().is_file()
else:
    DLL_PATH = None


def cpp_box_interpolation(intensity, qxy, qz,
                          qxy_start, qxy_step, qxy_size, qxy_window,
                          qz_start, qz_step, qz_size, qz_window):
    if not len(intensity) == len(qxy) == len(qz):
        raise ValueError(f'Lengths of provided vectors differ: '
                         f'{len(intensity)}, {len(qxy)}, {len(qz)}.')
    if not DLL_PATH or not DLL_PATH.is_file():
        return
    box_interpolation = ctypes.CDLL(str(DLL_PATH))
    size = len(intensity)
    inten = (ctypes.c_double * size)(*intensity)
    qxy_ = (ctypes.c_double * size)(*qxy)
    qz_ = (ctypes.c_double * size)(*qz)
    box_interpolation. \
        boxInterpolation. \
        argtypes = [ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.c_uint,
                    ctypes.c_double,
                    ctypes.c_double,
                    ctypes.c_uint,
                    ctypes.c_double,
                    ctypes.c_double,
                    ctypes.c_double,
                    ctypes.c_uint,
                    ctypes.c_double]
    box_interpolation. \
        boxInterpolation.restype = ctypes.POINTER(ctypes.c_double)
    res = box_interpolation. \
        boxInterpolation(inten, qxy_, qz_, size,
                         qxy_start, qxy_step, qxy_size, qxy_window,
                         qz_start, qz_step, qz_size, qz_window)

    final_result = np.array([res[i] for i in range(qxy_size * qz_size)]). \
        reshape((qxy_size, qz_size)).transpose()

    box_interpolation.deleteResult.argtypes = [ctypes.POINTER(ctypes.c_double)]
    box_interpolation.deleteResult.restype = None
    box_interpolation.deleteResult(res)

    return final_result
