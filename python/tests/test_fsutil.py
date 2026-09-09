"""Testes unitários de sanitização (paridade com FileSystemUtil)."""

from __future__ import annotations

from fsutil import sanitize_basename


def test_sanitize_keeps_simple_name():
    assert sanitize_basename("nota.txt") == "nota.txt"


def test_sanitize_strips_path():
    assert sanitize_basename(r"C:\tmp\nota.txt") == "nota.txt"
    assert sanitize_basename("../nota.txt") == "nota.txt"


def test_sanitize_rejects_dot_names():
    assert sanitize_basename(".") == ""
    assert sanitize_basename("..") == ""
    assert sanitize_basename("") == ""


def test_sanitize_replaces_invalid_chars():
    assert sanitize_basename("a<b>c:d.txt") == "a_b_c_d.txt"
