"""Helper for cleaning and composing NLT Primo book titles."""

import re


def clean_parallel_title(title: str) -> str:
    """Strip English or parallel titles matching ' = ...' pattern."""
    if not title:
        return ""
    return re.sub(r"\s*=\s*.*$", "", title).strip()


def clean_series_title(series: str) -> str:
    """Clean series title by stripping MARC subfields and parallel titles."""
    if not series:
        return ""
    cleaned = series.split("$$")[0].strip()
    return re.sub(r"\s*=\s*.*$", "", cleaned).strip()


def compose_primo_title(raw_title: str, raw_series: str = "") -> str:
    """Clean title, clean series, and prepend series if not already present."""
    clean_title = clean_parallel_title(raw_title)
    if not clean_title:
        return ""
    series = clean_series_title(raw_series)
    if series and not clean_title.startswith(series):
        return f"{series} {clean_title}"
    return clean_title
