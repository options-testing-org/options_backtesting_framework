from dataclasses import dataclass, field
from enum import Enum, StrEnum, Flag, auto
import datetime



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
    INITIALIZED = auto()
    TRADE_IS_OPEN = auto()
    TRADE_PARTIALLY_CLOSED = auto()
    TRADE_IS_CLOSED = auto()
    EXPIRED = auto()


class OptionSpreadType(StrEnum):
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



