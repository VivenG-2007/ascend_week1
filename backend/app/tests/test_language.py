import pytest

from app.services.language import detect_language, resolve_language


@pytest.mark.parametrize(
    "text,expected",
    [
        ("What is the bus timing?", "en"),
        ("బస్సు సమయం ఎంత?", "te"),
        ("fees last date ఎప్పుడు", "te"),
        ("12345 ???", "en"),
        ("Please share the CSE-B timetable for Monday and also ఏమిటి", "en"),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_resolve_prefers_explicit_choice():
    assert resolve_language("hello", "te") == "te"
    assert resolve_language("బస్సు", "en") == "en"
    assert resolve_language("బస్సు", "auto") == "te"
