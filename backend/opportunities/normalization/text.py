from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable


ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
TATWEEL = "\u0640"
WHITESPACE_RE = re.compile(r"\s+")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
LOOKUP_SEPARATOR_RE = re.compile(r"[-‐‑‒–—―/\\.]+")
PUNCTUATION_RE = re.compile(r"[^\w\s+#]+", re.UNICODE)

ARABIC_CHAR_RE = re.compile(r"[\u0600-\u06ff]")
LATIN_CHAR_RE = re.compile(r"[A-Za-zÀ-ÿ]")

ARABIC_TRANSLATION = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ئ": "ي",
        "ؤ": "و",
        "ة": "ه",
        "ۀ": "ه",
        "ک": "ك",
        "ی": "ي",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)

DISPLAY_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "`": "'",
    }
)


def clean_display_text(value: Any, *, max_length: int | None = None) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).translate(DISPLAY_TRANSLATION)
    text = CONTROL_CHARS_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip(" \t\r\n,;|")
    if max_length is not None:
        text = text[:max_length].rstrip()
    return text


def normalize_arabic(text: str) -> str:
    text = text.replace(TATWEEL, "")
    text = ARABIC_DIACRITICS_RE.sub("", text)
    return text.translate(ARABIC_TRANSLATION)


def strip_latin_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_lookup_key(value: Any) -> str:
    text = clean_display_text(value)
    if not text:
        return ""

    text = normalize_arabic(text)
    text = strip_latin_accents(text)
    text = text.casefold()
    text = text.replace("&", " and ")
    text = text.replace("_", " ")
    text = LOOKUP_SEPARATOR_RE.sub(" ", text)
    text = re.sub(r"['\"]+", " ", text)
    text = PUNCTUATION_RE.sub(" ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_token_set(value: Any) -> set[str]:
    return {token for token in normalize_lookup_key(value).split() if token}


def detect_language(value: Any) -> str:
    text = clean_display_text(value)
    if not text:
        return "unknown"
    has_arabic = bool(ARABIC_CHAR_RE.search(text))
    has_latin = bool(LATIN_CHAR_RE.search(text))
    if has_arabic and has_latin:
        return "mixed"
    if has_arabic:
        return "ar"
    if has_latin:
        return "latin"
    return "unknown"


def dedupe_texts(values: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_display_text(value)
        key = normalize_lookup_key(text)
        if not text or not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def title_case_latin(value: str) -> str:
    text = clean_display_text(value)
    if not text:
        return ""
    if ARABIC_CHAR_RE.search(text):
        return text

    words = []
    for word in text.split():
        if word.isupper() and len(word) <= 4:
            words.append(word)
        elif any(char in word for char in ("+", "#", ".")):
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


__all__ = [
    "clean_display_text",
    "dedupe_texts",
    "detect_language",
    "normalize_token_set",
    "normalize_arabic",
    "normalize_lookup_key",
    "strip_latin_accents",
    "title_case_latin",
]
