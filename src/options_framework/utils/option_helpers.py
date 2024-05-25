from options_framework.option import Option

def select_option_by_delta(options: list[Option], delta: float) -> Option | None:
    """
    Select an option with the nearest delta. If the delta is positive, the option with the next lower delta
    will be selected.
    If the delta is negative, the next higher (less negative) will be selected.

    :param options: list of options to select from
    :param delta: the target delta
    :return: an Option or None if no options could be found
    """
    return None