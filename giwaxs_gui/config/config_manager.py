import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_FOLDER = Path(__file__).parents[1] / 'user_config'
_DEFAULT_CONFIG_FOLDER = Path(__file__).parents[1] / 'static' / 'default_config'

if not _CONFIG_FOLDER.is_dir():
    _CONFIG_FOLDER.mkdir()


def read_config(config_name: str, get_default_values: bool = False):
    filename = f'{config_name}.json'
    config_path = _CONFIG_FOLDER / filename
    config_default_path = _DEFAULT_CONFIG_FOLDER / filename
    if get_default_values:
        return _read_config(config_default_path)
    else:
        saved_dict = _read_config(config_path)
        if not saved_dict:
            return _read_config(config_default_path)
        else:
            return saved_dict


def _read_config(path: Path):
    try:
        with open(str(path), 'r') as fp:
            saved_dict = json.load(fp)
            if type(saved_dict) is not dict:
                logger.error(f'JSON object is not dict:\n{saved_dict}')
            else:
                return saved_dict
    except FileNotFoundError:
        return
    except Exception as err:
        logger.exception(err)
        return


def save_config(config_name: str, config_dict: dict):
    config_path = _CONFIG_FOLDER / f'{config_name}.json'
    try:
        with open(config_path, 'w') as fp:
            json.dump(config_dict, fp)
    except Exception as err:
        logger.exception(err)
