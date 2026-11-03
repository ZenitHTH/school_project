"""Remote ISBN metadata providers: NLT Primo VE, SE-ED BFF, and Open Library."""

import json
import re
import ssl
import urllib.request
from typing import Dict, Optional

from core.library.services.seed_detail_parser import (
    DISALLOWED_PREFIXES,
    _collect_label_tokens,
    _collect_lexical_texts,
    _collect_multi_label_tokens,
    _collect_single_label_token,
    _extract_seed_detail,
    _find_multi_text,
    _find_next_text,
    _find_single_text,
    _is_label,
)

NLT_PRIMO_URL = "https://nlt.primo.exlibrisgroup.com/primaws/rest/pub/pnxs"
SEED_SEARCH_URL = "https://mp-api.se-ed.com/web-bff/search-product"
SEED_DETAIL_URL = "https://mp-api.se-ed.com/web-bff/physical-product"
OPENLIBRARY_URL = "https://openlibrary.org/api/books"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
UNKNOWN_PUBS = ("-ไม่ปรากฏสำนักพิมพ์", "ไม่ปรากฏสำนักพิมพ์", "ม.ป.พ.", "ม.ป.ท.")

__all__ = [
    "normalize_isbn",
    "is_valid_isbn",
    "is_arabic_isbn",
    "parse_nlt_primo_json",
    "parse_seed_product",
    "parse_openlibrary_json",
    "fetch_remote_providers",
    "_fetch_json",
    "_fetch_primo",
    "_fetch_seed",
    "_fetch_openlibrary",
    "_match_seed_sku",
    "_clean_primo_field",
    "_extract_primo_text",
    "_collect_lexical_texts",
    "_is_label",
    "_collect_single_label_token",
    "_collect_multi_label_tokens",
    "_collect_label_tokens",
    "_find_single_text",
    "_find_multi_text",
    "_find_next_text",
    "_extract_seed_detail",
    "DISALLOWED_PREFIXES",
    "UNKNOWN_PUBS",
]


def normalize_isbn(raw: str) -> str:
    """Strip whitespace and hyphens from raw ISBN and convert to uppercase."""
    return "".join(raw.split()).replace("-", "").upper() if raw else ""


def is_valid_isbn(isbn: str) -> bool:
    """Validate whether normalized ISBN is a valid 10 or 13-character ASCII string."""
    if not isbn or not isbn.isascii():
        return False
    if len(isbn) == 13:
        return isbn.isdigit()
    return len(isbn) == 10 and isbn[:-1].isdigit() and (isbn[-1].isdigit() or isbn[-1] == "X")


def is_arabic_isbn(raw: str) -> bool:
    """Validate that raw ISBN contains only Arabic digits and optional ISBN-10 check digit."""
    if not raw or not raw.strip():
        return False
    clean = "".join(raw.split()).replace("-", "")
    if not clean:
        return False
    if all(c in "0123456789" for c in clean):
        return True
    return len(clean) == 10 and all(c in "0123456789" for c in clean[:9]) and clean[9] in "Xx"


def _fetch_json(url: str, timeout: float = 5.0) -> dict:
    """Fetch JSON from URL with User-Agent header and default SSL context."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return json.loads(resp.read().decode(charset, errors="replace"))


def _clean_primo_field(val: str) -> str:
    return val.split("$$")[0].strip() if val else ""


def _extract_primo_text(container: dict, *keys: str) -> str:
    for key in keys:
        vals = container.get(key)
        cleaned = _clean_primo_field(str(vals[0])) if isinstance(vals, list) and vals and vals[0] else ""
        if cleaned:
            return cleaned
    return ""


def parse_nlt_primo_json(data: dict, isbn: str) -> Optional[Dict[str, str]]:
    """Parse NLT Primo VE JSON response to extract book metadata."""
    docs = data.get("docs") or []
    if not docs or not isinstance(docs[0], dict):
        return None
    pnx = docs[0].get("pnx") or {}
    addata, display = pnx.get("addata") or {}, pnx.get("display") or {}
    title = _extract_primo_text(addata, "btitle") or _extract_primo_text(display, "title")
    if not title:
        return None
    author = (_extract_primo_text(addata, "au", "creatorfull") or _extract_primo_text(display, "creator")).rstrip(".").strip()
    publisher = _extract_primo_text(addata, "pub") or _extract_primo_text(display, "publisher")
    return {"isbn": isbn, "title": title, "author": author or publisher, "publisher": publisher}


def _match_seed_sku(variants: list, isbn: str) -> bool:
    return not variants or any(normalize_isbn(str(v.get("sku", ""))) == isbn for v in variants if isinstance(v, dict))


def parse_seed_product(search_data: dict, detail_data: Optional[dict], isbn: str) -> Optional[Dict[str, str]]:
    """Parse SE-ED search and detail responses to extract book metadata."""
    products = search_data.get("products") or []
    if not products or not isinstance(products[0], dict):
        return None
    pp = ((products[0].get("physicalProduct") or {}).get("physicalProduct") or {})
    if not _match_seed_sku(pp.get("variants") or [], isbn):
        return None
    title = re.sub(r"^\[[^\]]+\]\s*", "", str(pp.get("name") or "")).strip()
    if not title:
        return None
    raw_author, publisher = _extract_seed_detail(detail_data)
    pub = "" if publisher in UNKNOWN_PUBS else publisher
    return {"isbn": isbn, "title": title, "author": raw_author or pub, "publisher": pub}


def parse_openlibrary_json(data: dict, isbn: str) -> Optional[Dict[str, str]]:
    """Parse Open Library book data JSON response."""
    book = data.get(f"ISBN:{isbn}")
    if not isinstance(book, dict) or not book.get("title"):
        return None
    title = str(book.get("title", "")).strip()
    authors = ", ".join(a.get("name", "").strip() for a in book.get("authors", []) if isinstance(a, dict) and a.get("name"))
    pubs = ", ".join(p.get("name", "").strip() for p in book.get("publishers", []) if isinstance(p, dict) and p.get("name"))
    return {"isbn": isbn, "title": title, "author": authors or pubs, "publisher": pubs}


def _fetch_primo(isbn: str, timeout: float) -> Optional[Dict[str, str]]:
    try:
        url = f"{NLT_PRIMO_URL}?vid=66NLT_INST:66NLT&q=isbn,exact,{isbn}&offset=0&limit=1&lang=th"
        return parse_nlt_primo_json(_fetch_json(url, timeout), isbn)
    except Exception:
        return None


def _fetch_seed_detail(prod_id: str, timeout: float) -> Optional[dict]:
    try:
        return _fetch_json(f"{SEED_DETAIL_URL}/{prod_id}", timeout) if prod_id else None
    except Exception:
        return None


def _fetch_seed(isbn: str, timeout: float) -> Optional[Dict[str, str]]:
    try:
        s_data = _fetch_json(f"{SEED_SEARCH_URL}?filter.keyword={isbn}&option.limit=1&option.skip=0", timeout)
        prods = s_data.get("products") or []
        if not prods or not isinstance(prods[0], dict):
            return None
        pp = ((prods[0].get("physicalProduct") or {}).get("physicalProduct") or {})
        d_data = _fetch_seed_detail(prods[0].get("id") or pp.get("id"), timeout)
        return parse_seed_product(s_data, d_data, isbn)
    except Exception:
        return None


def _fetch_openlibrary(isbn: str, timeout: float) -> Optional[Dict[str, str]]:
    try:
        url = f"{OPENLIBRARY_URL}?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        return parse_openlibrary_json(_fetch_json(url, timeout), isbn)
    except Exception:
        return None


def fetch_remote_providers(isbn: str, timeout: float = 5.0) -> Optional[Dict[str, str]]:
    """Chain remote JSON providers: NLT Primo VE -> SE-ED BFF -> Open Library."""
    step = min(timeout, 2.5)
    return _fetch_primo(isbn, step) or _fetch_seed(isbn, step) or _fetch_openlibrary(isbn, timeout)
