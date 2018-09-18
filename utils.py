# coding=utf-8
from datetime import timedelta, datetime
from typing import Optional


def cnvt_date(date_str, fmt='%Y-%m-%d'):
    try:
        date_str = datetime.strptime(date_str, fmt)
    except ValueError:
        date_str = None
    return date_str


def delta(start: str, end: str) -> Optional[timedelta]:
    dt_start = cnvt_date(start)
    dt_end = cnvt_date(end)

    if dt_start and dt_end:
        return dt_end - dt_start
    return None
