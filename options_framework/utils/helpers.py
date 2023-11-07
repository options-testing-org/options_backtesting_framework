from decimal import Context, Decimal, getcontext

def decimalize_0(value):
    """
    Floating numbers can produce unexpected results in calculation.
    Decimal numbers fix this. This returns a decimal number with 0 decimal places.
    :param value: the floating point number to decimalize
    :return: a decimal number rounded to 0 decimal places
    """
    dec_val = Decimal(value)
    quantize_val = dec_val.quantize(Decimal('1'))
    return quantize_val

def decimalize_2(value):
    """
    Floating numbers can produce unexpected results in calculation.
    Decimal numbers fix this. This returns a decimal number with 2 decimal places.
    :param value: the floating point number to decimalize
    :return: a decimal number rounded to 2 decimal places
    """
    dec_val = Decimal(value)
    quantize_val = dec_val.quantize(Decimal('1.00'))
    return quantize_val

def decimalize_4(value):
    """
    Floating numbers can produce unexpected results in calculation.
    Decimal numbers fix this. This returns a decimal number with 4 decimal places.
    :param value: the floating point number to decimalize
    :return: a decimal number rounded to 4 decimal places
    """
    dec_val = Decimal(value)
    quantize_val = dec_val.quantize(Decimal('1.0000'))
    return quantize_val

def distinct(iterable):
    """
    Returns a list of distinct items from a given iterable
    :param iterable:
    :return: list of distinct items
    """
    distinct_values = set()
    for x in iterable:
        if x in distinct_values:
            continue
        yield x
        distinct_values.add(x)
