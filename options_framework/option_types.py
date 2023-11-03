from enum import Enum


class OptionType(Enum):
    """
    The basic option type is either a put or a call
    """
    CALL = 1
    PUT = 2


class OptionPositionType(Enum):
    """
    If an option is bought to open, it is long. If it is sold to open, it is short.
    """
    SHORT = 1
    LONG = 2


class OptionCombinationType(Enum):
    """
    This is the type of predefined option combinations used.
    """
    SINGLE = 1
    VERTICAL = 2
    RATIO = 3
    CALENDAR = 4
    DIAGONAL = 5
    STRADDLE = 6
    STRANGLE = 7
    BUTTERFLY = 8
    IRON_BUTTERFLY = 9
    CONDOR = 10
    IRON_CONDOR = 11
    COLLAR = 12
    CUSTOM = 100


class OptionTradeType(Enum):
    """
    If the trade costs money to open, it is a debit trade.
    If the premium is net negative, meaning the trader received
    money to open the trade, it is a credit trade.
    """
    CREDIT = 1
    DEBIT = 2

