import pathlib
from options_framework import config


def test_project_root():
    assert config.settings.PROJECT_ROOT == pathlib.Path(__file__).parent.parent
    assert (
        config.settings.TEST_DATA_DIR
        == config.settings.PROJECT_ROOT / "tests" / "test_data"
    )


def test_settings_toml_exists():
    expected_settings_toml_path = config.settings.PROJECT_ROOT / "settings.toml"
    assert expected_settings_toml_path.exists()


def test_settings_toml_file_has_default_message():
    assert config.settings.DEFAULT_MESSAGE == "Config Default message"
