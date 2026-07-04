import os
import json
from typing import Any, Dict
from audioburst.config import Config


def load_config(config_path: str) -> Config:
    if os.path.exists(config_path):
        return Config.load(config_path)
    return Config()


def save_config(config: Config, config_path: str) -> None:
    config.save(config_path)


def merge_configs(base: Config, override: Dict[str, Any]) -> Config:
    data=base.to_dict()
    _deep_merge(data, override)
    return Config.from_dict(data)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key]=value
