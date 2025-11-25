import os
import tomllib
from pathlib import Path

config_folder = Path(os.getenv("OPTIONS_FRAMEWORK_CONFIG_FOLDER"))

def load_settings(settings_file):
    settings_path = config_folder.joinpath(settings_file)
    with open(settings_path, "rb") as f:
        return tomllib.load(f)

settings = load_settings("settings.toml")

