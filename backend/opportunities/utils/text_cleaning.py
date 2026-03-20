import re
import unicodedata


REPEATED_PUNCTUATION_PATTERN = re.compile(r"([!?.,;:])\1+")
WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_text(text: str) -> str:
    if text is None:
        return ""

    normalized_text = unicodedata.normalize("NFKC", str(text))
    lowered_text = normalized_text.lower()
    single_punctuation_text = REPEATED_PUNCTUATION_PATTERN.sub(r"\1", lowered_text)
    compact_text = WHITESPACE_PATTERN.sub(" ", single_punctuation_text)
    return compact_text.strip()

