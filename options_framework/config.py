import pathlib
from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=['settings.toml', '.secrets.toml'],
)

settings.PROJECT_ROOT = pathlib.Path(__file__).parent.parent
settings.TEST_DATA_DIR = settings.PROJECT_ROOT / 'tests' / 'test_data'
# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
