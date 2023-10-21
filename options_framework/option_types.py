from enum import Enum


"""
The basic option type is either a put or a call
"""
class OptionType(Enum):
    CALL = 1
    PUT = 2

"""
If an option is bought to open, it is long. If it is sold to open, it is short.
"""
class OptionPositionType(Enum):
    SHORT = 1
    LONG = 2


class OptionCombinationType(Enum):
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


class OptionTradeType(Enum):
    CREDIT = 1
    DEBIT = 2

