"""Tests for the US-English text normalizer."""
from script.normalizer import normalize, number_to_words


def test_small_numbers():
    assert number_to_words(0) == "zero"
    assert number_to_words(7) == "seven"
    assert number_to_words(13) == "thirteen"
    assert number_to_words(40) == "forty"
    assert number_to_words(55) == "fifty-five"
    assert number_to_words(100) == "one hundred"
    assert number_to_words(342) == "three hundred forty-two"


def test_large_numbers():
    assert number_to_words(1000) == "one thousand"
    assert "million" in number_to_words(2_500_000)
    assert number_to_words(-5) == "minus five"


def test_years():
    result = normalize("It was 1995, not 2004.")
    assert "nineteen ninety five" in result
    assert "two thousand four" in result
    result = normalize("By 2026 everything changed.")
    assert "twenty twenty six" in result


def test_currency():
    result = normalize("She paid $12.50 for the ticket.")
    assert "twelve dollars" in result
    assert "cents" in result
    result = normalize("The total was $1,000.")
    assert "one thousand dollars" in result


def test_percentage():
    result = normalize("42% agreed.")
    assert "forty-two percent" in result


def test_time():
    result = normalize("The train left at 11:58 exactly.")
    assert "eleven fifty-eight" in result.replace("fifty eight",
                                                  "fifty-eight")


def test_measurements():
    result = normalize("He ran 5 mph for 3 miles.")
    assert "five miles per hour" in result
    assert "three miles" in result


def test_dates():
    result = normalize("They met on March 15, 2019 in Ohio.")
    assert "March fifteenth" in result
    assert "twenty nineteen" in result


def test_abbreviations():
    result = normalize("Mr. Smith and Dr. Jones met Mrs. Brown.")
    assert "Mr Smith" in result or "Mr. Smith" in result


def test_plain_text_unchanged():
    text = "The quick brown fox jumps over the lazy dog."
    assert normalize(text) == text
