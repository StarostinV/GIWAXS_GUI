import pytest
from pathlib import Path

__all__ = ['create_tmp_user_config_dir', 'tmp_user_config_dir', 'default_config',
           'default_interpolated_config', 'user_interpolated_config',
           'get_default_values_arg']


@pytest.fixture(scope='session')
def create_tmp_user_config_dir(tmpdir_factory):
    """Creates temporary user_config dir."""
    return tmpdir_factory.mktemp('user_config')


@pytest.fixture()
def tmp_user_config_dir(create_tmp_user_config_dir, monkeypatch):
    """Set tmp user dir to _CONFIG_FOLDER."""
    monkeypatch.setattr('giwaxs_gui.config.config_manager._CONFIG_FOLDER', Path(create_tmp_user_config_dir))
    return create_tmp_user_config_dir


DEFAULT_CONFIG_PARAMS = (
    ('Baseline correction', {"smoothness_param": 1000, "asymmetry_param": 0.01}),
    ('Fitting parameters', {"max_peaks_number": 20, "init_width": 30.0, "sigma_find": 8.0, "sigma_fit": None}),
    ('Interpolation parameters', {"r_size": 512, "phi_size": 512, "mode": "Bilinear"})
)

USER_CONFIG_INTERPOLATED_PARAMS = (
    {"r_size": 200, "phi_size": 100, "mode": "Cubic"},
    {"r_size": 256, "phi_size": 512, "mode": "Bilinear"}
)


@pytest.fixture(params=DEFAULT_CONFIG_PARAMS, ids=lambda val: val[0])
def default_config(request):
    return request.param


@pytest.fixture()
def default_interpolated_config():
    return {"r_size": 512, "phi_size": 512, "mode": "Bilinear"}


@pytest.fixture(params=USER_CONFIG_INTERPOLATED_PARAMS)
def user_interpolated_config(request):
    return request.param


@pytest.fixture(params=[True, False], ids=['default True', 'default False'])
def get_default_values_arg(request):
    return request.param
