import pathlib
from dynaconf import Dynaconf
import os

settings = Dynaconf(
    envvar_prefix="OPT_TESTING",
    settings_files=["config/settings.toml", "config/.secrets.toml"],
)

settings.PROJECT_ROOT = pathlib.Path(__file__).parent.parent

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
