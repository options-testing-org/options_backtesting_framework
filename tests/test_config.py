import pathlib
import pytest
from dynaconf import Dynaconf
from options_framework import config

def test_project_root():
    assert config.settings.PROJECT_ROOT == pathlib.Path(__file__).parent.parent

def test_settings_toml_exists():
    assumed_path = config.settings.PROJECT_ROOT / "settings.toml"
    assert assumed_path.exists()

def test_settings_toml_file_has_default_message():
    assert config.settings.DEFAULT_MESSAGE == "Default message"
