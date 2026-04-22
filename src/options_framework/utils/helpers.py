from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Generator
from pathlib import Path
import calendar
import duckdb

import pandas as pd

from ..config import settings


def decimalize_0(value: int | float | Decimal) -> Decimal:
    """
    Floating numbers can produce unexpected results in calculation.
    Decimal numbers fix this. This returns a decimal number with 0 decimal places.
    :param value: the floating point number to decimalize
    :return: a decimal number rounded to 0 decimal places
    """
    dec_val = Decimal(value)
    quantize_val = dec_val.quantize(Decimal('1'))
    return quantize_val

def decimalize_2(value: float | Decimal) -> Decimal:
    """
    Floating numbers can produce unexpected results in calculation.
    Decimal numbers fix this. This returns a decimal number with 2 decimal places.
    :param value: the floating point number to decimalize
    :return: a decimal number rounded to 2 decimal places
    """
    dec_val = Decimal(value)
    quantize_val = dec_val.quantize(Decimal('1.00'))
    return quantize_val

def decimalize_4(value: float | Decimal) -> Decimal:
    """
    Floating numbers can produce unexpected results in calculation.
    Decimal numbers fix this. This returns a decimal number with 4 decimal places.
    :param value: the floating point number to decimalize
    :return: a decimal number rounded to 4 decimal places
    """
    dec_val = Decimal(value)
    quantize_val = dec_val.quantize(Decimal('1.0000'))
    return quantize_val

def distinct(iterable: list) -> Generator[Any, Any, None]:
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

def month_range(start_dt: datetime.datetime, end_dt: datetime.date) -> list[tuple[int, int]]:
    """
    Return list of (year, month) tuples covering the date range.
    """

    months = []
    year, month = start_dt.year, start_dt.month
    while (year, month) <= (end_dt.year, end_dt.month):
        months.append((year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1

    return months

def get_witching_dates(start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
    start_year = start_date.year
    end_year = end_date.year
    years = range(start_year, end_year + 1)
    dates = []
    for year in years:
        for month in [3, 6, 9, 12]:
            # Find third Friday
            c = calendar.monthcalendar(year, month)
            # Third Friday: first week with a Friday counts as week 1
            fridays = [week[calendar.FRIDAY] for week in c if week[calendar.FRIDAY] != 0]
            dates.append(date(year, month, fridays[2]))
    return dates


def get_market_dates(start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
    options_dir = Path(settings['options_directory'])
    market_dates_fn = options_dir.joinpath('market_holidays.csv')
    df_holidays = pd.read_csv(market_dates_fn, parse_dates=['date'])
    df_holidays = df_holidays[(df_holidays['date'] >= pd.Timestamp(start_date)) & (df_holidays['date'] <= pd.Timestamp(end_date))]
    exclude_shortdays = settings.get('exclude_shortdays')
    exclude_economic = settings.get('exclude_economic')

    # always exclude market closed days
    mask = df_holidays['status'] == 'closed'
    if exclude_shortdays:
        shortdays_mask = df_holidays['status'] == 'short day'
        mask = mask | shortdays_mask
    # exclude all economic days - witching, fomc, ppi, cpi
    if exclude_economic:
        economic_mask = df_holidays['status'] == 'economic'
        mask = mask | economic_mask
    else:
        # selectively exclude economic days
        exclude_witching = settings.get('exclude_witching')
        if exclude_witching:
            witching_mask = df_holidays['holiday_name'].str.contains('witching')
            mask = mask | witching_mask
        exclude_fomc = settings.get('exclude_fomc')
        if exclude_fomc:
            fomc_mask = df_holidays['holiday_name'].str.contains('fomc')
            mask = mask | fomc_mask
        exclude_ppi = settings.get('exclude_ppi')
        if exclude_ppi:
            ppi_mask = df_holidays['holiday_name'].str.contains('ppi')
            mask = mask | ppi_mask
        exclude_cpi = settings.get('exclude_cpi')
        if exclude_cpi:
            cpi_mask = df_holidays['holiday_name'].str.contains('cpi')
            mask = mask | cpi_mask

    df_holidays = df_holidays[mask]

    market_days_list = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:
            if not df_holidays['date'].eq(pd.Timestamp(current_date)).any():
                market_days_list.append(current_date)
        current_date += datetime.timedelta(days=1)
    return market_days_list





