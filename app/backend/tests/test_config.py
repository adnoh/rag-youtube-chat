"""Tests for config.py parsing helpers."""

from backend.config import _parse_origins


def test_parse_origins_default_produces_two_entries():
    result = _parse_origins("http://localhost:5173,http://127.0.0.1:5173")
    assert result == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_parse_origins_strips_whitespace():
    result = _parse_origins("  http://localhost:5173 , http://127.0.0.1:5173  ")
    assert result == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_parse_origins_ignores_trailing_comma():
    result = _parse_origins("http://localhost:5173,")
    assert result == ["http://localhost:5173"]


def test_parse_origins_empty_string_returns_empty_list():
    result = _parse_origins("")
    assert result == []


def test_parse_origins_blank_only_string_returns_empty_list():
    result = _parse_origins("  ,  ,  ")
    assert result == []


def test_parse_origins_single_origin():
    result = _parse_origins("https://myapp.example.com")
    assert result == ["https://myapp.example.com"]
