import pytest
from giwaxs_gui.config import config_manager


@pytest.mark.slow
def test_read_default_config(tmp_user_config_dir, default_config,
                             get_default_values_arg):
    """
    config_manager.read_config should return dict with default
    parameters when arg get_default_values=True or if there is no user config
    """
    name = default_config[0]
    expected_params = default_config[1]
    params = config_manager.read_config(name, get_default_values=get_default_values_arg)
    assert expected_params == params


def test_wrong_config_name(get_default_values_arg):
    """
    config_manager.read_config should return None if
    there is no default config found
    """
    wrong_config_name = 'Wrong config name!'
    params = config_manager.read_config(wrong_config_name, get_default_values_arg)
    assert params is None


def test_read_user_config(tmp_user_config_dir,
                          user_interpolated_config,
                          default_interpolated_config):
    """
    config_manager.save_config should save config to user_config folder
    """
    name = 'Interpolation parameters'
    config_manager.save_config(name, user_interpolated_config)
    assert any([local.fnmatch(f'*{name}.json')
                for local in tmp_user_config_dir.listdir()])
    read_config = config_manager.read_config(name)
    assert read_config == user_interpolated_config
    read_default_config = config_manager.read_config(name, get_default_values=True)
    assert read_default_config == default_interpolated_config


