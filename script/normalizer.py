"""US-English text normalization for TTS.

Converts written forms that neural TTS models read badly into natural
spoken US English: numbers, dates, currency, percentages, years,
measurements, common abbreviations and URLs.
"""
from __future__ import annotations

import re

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty",
         "sixty", "seventy", "eighty", "ninety"]
_SCALES = [(1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")]


def number_to_words(number: int) -> str:
    if number < 0:
        return "minus " + number_to_words(-number)
    if number < 20:
        return _ONES[number]
    if number < 100:
        tens = _TENS[number // 10]
        rest = number % 10
        return tens if rest == 0 else f"{tens}-{_ONES[rest]}"
    for scale_value, scale_word in _SCALES:
        if number >= scale_value:
            head = number_to_words(number // scale_value)
            tail = number % scale_value
            if tail == 0:
                return f"{head} {scale_word}"
            # US English omits "and" (two thousand four, one thousand five).
            parts = f"{head} {scale_word} {number_to_words(tail)}"
            return re.sub(r"\s+", " ", parts).strip()
    hundreds = number_to_words(number // 100)
    rest = number % 100
    return hundreds + (" hundred" if rest == 0 else f" hundred {number_to_words(rest)}")


def _year_to_words(year_text: str) -> str:
    """Speak years the way US English speakers do.

    1995 -> "nineteen ninety five", 2004 -> "two thousand four",
    2026 -> "twenty twenty six". Other ranges fall back to full numbers.
    """
    year = int(year_text)
    if 1000 <= year <= 1999 or 2010 <= year <= 2099:
        high, low = divmod(year, 100)
        low_word = number_to_words(low).replace("-", " ") if low else "hundred"
        return f"{number_to_words(high)} {low_word}"
    return number_to_words(year)


def _spell_digits(digits: str) -> str:
    return " ".join(_ONES[int(d)] if d.isdigit() else d for d in digits)


_CURRENCY_SYMBOLS = {"$": "dollars", "€": "euros", "£": "pounds"}


def _fractional_words(fraction: str) -> str:
    return " point " + " ".join(_ONES[int(d)] for d in fraction)


def normalize_decimal(int_part: str, frac_part: str) -> str:
    words = number_to_words(int(int_part))
    return words + _fractional_words(frac_part) if frac_part else words


def normalize_number_token(token: str) -> str:
    """Normalize a bare numeric token (with optional commas / decimals)."""
    negative = token.startswith("-")
    token = token.lstrip("-")
    whole, _, frac = token.partition(".")
    whole_clean = whole.replace(",", "")
    if frac:
        text = normalize_decimal(whole_clean or "0", frac)
    elif len(whole_clean.replace(",", "")) > 9:
        text = " ".join(_spell_digits(whole_clean))
        return ("minus " if negative else "") + text
    else:
        text = number_to_words(int(whole_clean))
    return ("minus " if negative else "") + text


# --- regex passes -----------------------------------------------------------

RE_URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
RE_MONEY = re.compile(r"([$€£])(\d[\d,]*(?:\.\d+)?)")
RE_PERCENT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*%")
RE_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})s?\b(?!\.?\d)")
RE_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")
RE_NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\d])")
RE_ABBREV = re.compile(
    r"\b(Mr|Mrs|Ms|Dr|Prof|St|Ave|Blvd)\.(?=\s+[A-Z])", re.IGNORECASE
)
RE_MEASURE = re.compile(
    r"\b(\d[\d,]*(?:\.\d+)?)\s*(km|kg|lb[s]?|mph|miles?|feet|foot|ft|meters?|m|cm|mm)\b",
    re.IGNORECASE,
)
_MEASURE_WORDS = {
    "km": "kilometers", "kg": "kilograms", "lb": "pounds", "lbs": "pounds",
    "mph": "miles per hour", "mile": "miles", "miles": "miles",
    "feet": "feet", "foot": "feet", "ft": "feet",
    "meter": "meters", "meters": "meters", "m": "meters",
    "cm": "centimeters", "mm": "millimeters",
}

MONTHS = [
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
]
_RE_DATE_MDY = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+(\d{4})\b", re.IGNORECASE,
)

_MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _month_name(token: str) -> str:
    key = token.lower().rstrip(".")
    if key in _MONTH_ABBR:
        return MONTHS[_MONTH_ABBR[key] - 1]
    return token.capitalize()


def normalize_dates(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        month = _month_name(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if day % 100 in (11, 12, 13):
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        day_word = f"{number_to_words(day)}{suffix}" if day <= 31 else number_to_words(day)
        return f"{month} {day_word}, {_year_to_words(str(year))}"

    return _RE_DATE_MDY.sub(replace, text)


def normalize_urls(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        url = match.group(0)
        spoken = (
            url.replace("https://", "").replace("http://", "")
            .replace("www.", "w w w dot ")
            .replace(".com", " dot com").replace(".org", " dot org")
            .replace(".net", " dot net").replace(".io", " dot i o")
            .replace("/", " slash ").replace("-", " dash ")
            .replace("_", " underscore ")
        )
        return spoken

    return RE_URL.sub(replace, text)


def normalize(text: str) -> str:
    """Full normalization pass; order matters."""
    text = normalize_urls(text)
    text = RE_ABBREV.sub(lambda m: m.group(1), text)

    def money_replace(match: re.Match[str]) -> str:
        symbol, amount = match.group(1), match.group(2)
        unit = _CURRENCY_SYMBOLS.get(symbol, symbol)
        whole, _, cents = amount.partition(".")
        words = number_to_words(int(whole.replace(",", "")))
        if cents:
            cent_words = " ".join(_ONES[int(d)] for d in cents[:2])
            return f"{words} {unit} and {cent_words} cents"
        return f"{words} {unit}"

    text = RE_MONEY.sub(money_replace, text)

    text = RE_PERCENT.sub(lambda m: f"{normalize_number_token(m.group(1))} percent", text)

    def time_replace(match: re.Match[str]) -> str:
        hour, minute = int(match.group(1)), int(match.group(2))
        hour_word = number_to_words(hour)
        minute_word = "o'clock" if minute == 0 else (
            f"{_ONES[minute // 10]} {_ONES[minute % 10]}" if minute < 10
            else number_to_words(minute)
        )
        return f"{hour_word} {minute_word}".strip()

    text = RE_TIME.sub(time_replace, text)

    def measure_replace(match: re.Match[str]) -> str:
        value, unit = match.group(1), match.group(2).lower()
        word = _MEASURE_WORDS.get(unit, unit)
        return f"{normalize_number_token(value)} {word}"

    text = RE_MEASURE.sub(measure_replace, text)
    text = normalize_dates(text)

    def year_replace(match: re.Match[str]) -> str:
        return _year_to_words(match.group(1))

    text = RE_YEAR.sub(year_replace, text)
    text = RE_NUMBER.sub(lambda m: normalize_number_token(m.group(0)), text)
    return re.sub(r"[ \t]{2,}", " ", text)
