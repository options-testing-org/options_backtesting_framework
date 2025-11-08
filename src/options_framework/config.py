from pathlib import Path
import tomllib
import os
from pathlib import Path

config_folder = Path(os.getenv("OPTIONS_FRAMEWORK_CONFIG_FOLDER"))

def load_settings(settings_file):
    settings_path = config_folder.joinpath(settings_file)
    with open(settings_path, "rb") as f:
        return tomllib.load(f)

settings = load_settings("settings.toml")
data_settings_file = settings['data_format_settings']
data_settings = load_settings(data_settings_file)
settings['data_settings'] = data_settings
pass
# self.data_format_settings = config.load_settings(settings['data_format_settings'])
#data_format_settings = load_settings(settings['data_format_settings'])


# from dynaconf import Dynaconf
# import os
#
# settings = Dynaconf(
#     envvar_prefix="OPT_TESTING",
#     settings_files=["config/settings.toml", "config/.secrets.toml"],
# )
#
# settings.PROJECT_ROOT = pathlib.Path(__file__).parent.parent

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
