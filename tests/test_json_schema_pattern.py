from __future__ import annotations

import re

import pytest

from itemadapter._json_schema import json_schema_pattern

SPACE_BODY = (
    r"\u0009-\u000D\u001C-\u0020\u0085\u00A0\u1680\u2000-\u200A\u2028-\u2029\u202F\u205F\u3000"
)
SPACE = f"[{SPACE_BODY}]"
ASCII_SPACE_BODY = r"\u0009-\u000D\u0020"
ASCII_SPACE = f"[{ASCII_SPACE_BODY}]"


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        # Shared syntax.
        (r"^[A-Za-z]+$", r"^[A-Za-z]+$"),
        (r"\fD[0-9]{2}\v", r"\fD[0-9]{2}\v"),
        (r"a(b|c)?(?:d)(?=e)(?!f)\.\\", r"a(b|c)?(?:d)(?=e)(?!f)\.\\"),
        (r"\x41\u00e9\t\n", r"\x41\u00e9\t\n"),
        (r"(a)\1", r"(a)\1"),
        (r"[a\]b^-]", r"[a\]b^-]"),
        (r"[a.b]", r"[a.b]"),
        (r"(?<=a)b", r"(?<=a)b"),
        (r"(?<!a)b", r"(?<!a)b"),
        (r"a{2", r"a{2"),
        # Translated syntax.
        (r"\Aab\Z", r"^ab$"),
        (r"(?P<year>[0-9]{4})", r"([0-9]{4})"),
        (r"a(?#comment)b", r"ab"),
        (r"(?s)a.b", r"a[\s\S]b"),
        (re.compile(r"a.b", re.DOTALL), r"a[\s\S]b"),
        ("(?x)a  # comment\n  [0-9]+", r"a[0-9]+"),
        (re.compile("a  # comment\n  b", re.VERBOSE), r"ab"),
        (r"(?ax)a b", r"ab"),
        ("(?x)a # unterminated comment", "a"),
        # Shorthand escapes that match different characters in Python and in
        # ECMA-262 are translated when they match few enough characters, and
        # omitted otherwise.
        (r"\s", SPACE),
        (r"\S", f"[^{SPACE_BODY}]"),
        (r"a\s+b", f"a{SPACE}+b"),
        (r"[\s,]", f"[{SPACE_BODY},]"),
        (r"[^\s]", f"[^{SPACE_BODY}]"),
        (r"\d", None),
        (r"\d{4}-\d{2}", None),
        (r"[\d.]", None),
        (r"[\s\d]", None),
        # Classes that match every character, or none, in both dialects.
        (r"[\s\S]", r"[\s\S]"),
        (r"[\S\s]", r"[\s\S]"),
        (r"[\d\D]", r"[\s\S]"),
        (r"[\w\W]", r"[\s\S]"),
        (r"[\d\Dx]", r"[\s\S]"),
        (r"[^\s\S]", r"[^\s\S]"),
        (r"(?a)[\s\S]", r"[\s\S]"),
        (r"(?a)[\w\W]", r"[\s\S]"),
        (r"\D", None),
        (r"[^\d]", None),
        (r"[\D]", None),
        (r"[^\d,]", None),
        (r"[\S]", None),
        (r"\w", None),
        (r"\W", None),
        (r"[\w-]", None),
        (r"[\W]", None),
        (r"\bfoo\b", None),
        (r"\B", None),
        (r"[\b]", r"[\b]"),
        # With re.ASCII, \d, \D, \w, \W, \b and \B mean the same in both
        # dialects, while \s and \S still need translating.
        (r"(?a)\d\D\w\W\b\B", r"\d\D\w\W\b\B"),
        (r"(?a)\s", ASCII_SPACE),
        (r"(?a)\S", f"[^{ASCII_SPACE_BODY}]"),
        (r"(?a)a\s+b", f"a{ASCII_SPACE}+b"),
        (r"(?a)[\s,]", f"[{ASCII_SPACE_BODY},]"),
        (r"(?a)[^\s]", f"[^{ASCII_SPACE_BODY}]"),
        (r"(?a)[\S]", None),
        (r"(?a)[^\S]", None),
        (re.compile(r"\bD\d{2}[\w\d]\b", re.ASCII), r"\bD\d{2}[\w\d]\b"),
        (re.compile(r"[^\d]", re.ASCII), r"[^\d]"),
        (r"(?a)[\B]", None),
        # Python-only syntax.
        (r"\a", None),
        (r"[\a]", None),
        (r"\N{BULLET}", None),
        (r"\U0001F600", None),
        (r"(?P=name)", None),
        (r"(?i)a", None),
        (re.compile(r"a", re.IGNORECASE), None),
        (r"(?m)a", None),
        (r"(?i:a)", None),
        (r"(?>a)", None),
        (r"a*+", None),
        (r"a{2,3}+", None),
        # Syntax that both dialects accept with a different meaning.
        (r"[]]", None),
        (r"[^]]", None),
        (r"\0", None),
        (r"\01", None),
        (r"(?x)a{2, 3}", None),
        # Malformed patterns.
        ("\\", None),
        (r"[abc", None),
        (r"\x4", None),
        (r"(?#unterminated", None),
        (r"(?P<unterminated", None),
    ],
)
def test_json_schema_pattern(pattern: str | re.Pattern[str], expected: str | None) -> None:
    assert json_schema_pattern(pattern) == expected


@pytest.mark.parametrize(
    ("shorthand", "flags"),
    [
        (r"[\s,]", 0),
        (r"[\s,]", re.ASCII),
    ],
)
def test_json_schema_pattern_space_equivalence(shorthand: str, flags: int) -> None:
    r"""The translation of \s matches exactly the characters that the original
    does. All of them are in the Basic Multilingual Plane, so the result is the
    same with and without the ``u`` flag."""
    translation = json_schema_pattern(re.compile(shorthand, flags))
    assert translation is not None
    source_regex = re.compile(shorthand, flags)
    translated_regex = re.compile(translation)
    for code_point in range(0x110000):
        character = chr(code_point)
        expected = source_regex.fullmatch(character) is not None
        actual = translated_regex.fullmatch(character) is not None
        assert actual == expected, hex(code_point)
