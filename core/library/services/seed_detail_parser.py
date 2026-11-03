"""Helper parsers for extracting metadata from SE-ED Lexical AST JSON."""

import json
from typing import Any, List, Optional, Tuple

DISALLOWED_PREFIXES = (
    "ผู้เขียน", "สำนักพิมพ์", "ISBN", "ขนาด", "ราคา",
    "ข้อมูลหนังสือ", "คำค้นหา", "เนื้อหา", "สารบัญ",
    "รหัสสินค้า", "เดือนปี", "ชนิดกระดาษ", "เนื้อในพิมพ์", "น้ำหนัก"
)

__all__ = [
    "DISALLOWED_PREFIXES",
    "_collect_lexical_texts",
    "_is_label",
    "_collect_single_label_token",
    "_collect_multi_label_tokens",
    "_collect_label_tokens",
    "_find_single_text",
    "_find_multi_text",
    "_find_next_text",
    "_extract_seed_detail",
]


def _collect_lexical_texts(val: Any, texts: List[str]) -> None:
    """Recursively extract plain text tokens from SE-ED Lexical AST."""
    if isinstance(val, dict):
        text = val.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
        for child in val.values():
            _collect_lexical_texts(child, texts)
    elif isinstance(val, list):
        for item in val:
            _collect_lexical_texts(item, texts)


def _is_label(tok: str) -> bool:
    """Determine whether token is a field label or separator."""
    clean = tok.replace("\xa0", "").strip()
    return clean.endswith(":") or clean.startswith(DISALLOWED_PREFIXES)


def _collect_single_label_token(following: List[str]) -> str:
    """Collect the first value token following a metadata label."""
    for raw in following:
        token = raw.strip()
        if not token or token in (":", "-"):
            continue
        if _is_label(token):
            return ""
        return token
    return ""


def _collect_multi_label_tokens(following: List[str]) -> str:
    """Collect comma-separated value tokens following a metadata label."""
    parts: List[str] = []
    expect_value = True
    for raw in following:
        token = raw.strip()
        if not parts and token in (":", "-", ""):
            continue
        if not token or _is_label(token):
            break
        if token == ",":
            expect_value = True
            continue
        if not expect_value:
            break
        parts.append(token)
        expect_value = False
    return ", ".join(parts)


def _collect_label_tokens(following: List[str], allow_multi: bool = True) -> str:
    """Compatibility wrapper delegating to single or multi label collector."""
    return _collect_multi_label_tokens(following) if allow_multi else _collect_single_label_token(following)


def _find_single_text(texts: List[str], prefix: str) -> str:
    """Find a single text value associated with a prefix in extracted Lexical tokens."""
    for idx, item in enumerate(texts):
        if item.startswith(prefix):
            inline = item[len(prefix):].lstrip(" :\xa0-").strip()
            val = inline or _collect_single_label_token(texts[idx + 1:])
            if val:
                return val
    return ""


def _find_multi_text(texts: List[str], prefix: str) -> str:
    """Find multi-value text associated with a prefix in extracted Lexical tokens."""
    for idx, item in enumerate(texts):
        if item.startswith(prefix):
            inline = item[len(prefix):].lstrip(" :\xa0-").strip()
            val = inline or _collect_multi_label_tokens(texts[idx + 1:])
            if val:
                return val
    return ""


def _find_next_text(texts: List[str], prefix: str, allow_multi: bool = True) -> str:
    """Compatibility wrapper delegating to single or multi text finder."""
    return _find_multi_text(texts, prefix) if allow_multi else _find_single_text(texts, prefix)


def _extract_seed_detail(detail_data: Optional[dict]) -> Tuple[str, str]:
    """Parse detail JSON to extract author and publisher."""
    detail_str = ((detail_data or {}).get("physicalProduct") or {}).get("detail", "")
    if not isinstance(detail_str, str) or not detail_str:
        return "", ""
    try:
        texts: List[str] = []
        _collect_lexical_texts(json.loads(detail_str), texts)
        return _find_multi_text(texts, "ผู้เขียน"), _find_single_text(texts, "สำนักพิมพ์")
    except Exception:
        return "", ""
