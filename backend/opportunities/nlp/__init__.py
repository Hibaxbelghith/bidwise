"""
Lightweight public NLP facade.

The implementation still lives in the existing preprocessing modules; this
package gives callers a clearer import surface while the internals remain
unchanged.
"""

from opportunities.nlp.nlp_preprocessing import (
    build_embedding_text,
    clean_text,
    extract_organization,
    prepare_text_for_nlp,
)

__all__ = [
    "clean_text",
    "extract_organization",
    "prepare_text_for_nlp",
    "build_embedding_text",
]
