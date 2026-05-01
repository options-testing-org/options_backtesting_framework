from .spread_base import SpreadBase
from ..option_types import OptionSpreadType

@dataclass(repr=False, slots=True)
class Collar(SpreadBase):
    pass
