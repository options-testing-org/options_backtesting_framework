from dataclasses import dataclass, field
from enum import Enum, StrEnum, Flag, auto


class OptionType(Enum):
    """
    The basic option type is either a put or a call
    """
    CALL = 1
    PUT = 2


class TransactionType(Enum):
    """
    A transaction is either a buy or a sell
    """
    BUY = 1
    SELL = 2


class OptionPositionType(Enum):
    """
    If an option is bought to open, it is long. If it is sold to open, it is short.
    """
    SHORT = 1
    LONG = 2


class OptionStatus(Flag):
    CREATED = auto()
    INITIALIZED = auto()
    EXPIRED = auto()
    TRADE_IS_OPEN = auto()
    TRADE_PARTIALLY_CLOSED = auto()
    TRADE_IS_CLOSED = auto()


class OptionCombinationType(StrEnum):
    """
    This is the type of predefined option combinations used.
    """
    SINGLE = auto()
    VERTICAL = auto()
    RATIO = auto()
    CALENDAR = auto()
    DIAGONAL = auto()
    STRADDLE = auto()
    STRANGLE = auto()
    BUTTERFLY = auto()
    IRON_BUTTERFLY = auto()
    CONDOR = auto()
    IRON_CONDOR = auto()
    COLLAR = auto()
    CUSTOM = auto()


class OptionTradeType(Enum):
    """
    If the trade costs money to open, it is a debit trade.
    If the premium is net negative, meaning the trader received
    money to open the trade, it is a credit trade.
    """
    CREDIT = 1
    DEBIT = 2


@dataclass
class FilterRange:
    low: float = None
    high: float = None

@dataclass
class SelectFilter:
    symbol: str
    option_type: OptionType = None
    expiration_range: FilterRange = field(default_factory=lambda: FilterRange())
    strike_range: FilterRange = field(default_factory=lambda: FilterRange())
    delta_range: FilterRange = field(default_factory=lambda: FilterRange())
    gamma_range: FilterRange = field(default_factory=lambda: FilterRange())
    theta_range: FilterRange = field(default_factory=lambda: FilterRange())
    vega_range: FilterRange = field(default_factory=lambda: FilterRange())
    rho_range: FilterRange = field(default_factory=lambda: FilterRange())
    open_interest_range: FilterRange = field(default_factory=lambda: FilterRange())
    implied_volatility_range: FilterRange = field(default_factory=lambda: FilterRange())
