"""Remote ISBN metadata providers: NLT Primo VE, SE-ED BFF, and Open Library."""

import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

NLT_PRIMO_URL = "https://nlt.primo.exlibrisgroup.com/primaws/rest/pub/pnxs"
SEED_SEARCH_URL = "https://mp-api.se-ed.com/web-bff/search-product"
SEED_DETAIL_URL = "https://mp-api.se-ed.com/web-bff/physical-product"
OPENLIBRARY_URL = "https://openlibrary.org/api/books"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DISALLOWED_PREFIXES = ("ผู้เขียน", "สำนักพิมพ์", "ISBN", "ขนาด", "ราคา", "ข้อมูลหนังสือ", "คำค้นหา")


def normalize_isbn(raw: str) -> str:
    """Strip whitespace and hyphens from raw ISBN and convert to uppercase."""
    return "".join(raw.split()).replace("-", "").upper() if raw else ""


def is_valid_isbn(isbn: str) -> bool:
    """Validate whether normalized ISBN is a valid 10 or 13-character string."""
    if not isbn:
        return False
    if len(isbn) == 13:
        return isbn.isdigit()
    return len(isbn) == 10 and isbn[:-1].isdigit() and (isbn[-1].isdigit() or isbn[-1] == "X")


def _fetch_json(url: str, timeout: float = 5.0) -> dict:
    """Fetch JSON from URL with User-Agent header and default SSL context."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return json.loads(resp.read().decode(charset, errors="replace"))


def _clean_primo_field(val: str) -> str:
    return val.split("$$")[0].strip() if val else ""


def _extract_primo_text(container: dict, *keys: str) -> str:
    """Extract first non-empty text from prioritized keys in container."""
    for key in keys:
        vals = container.get(key)
        if isinstance(vals, list) and vals and vals[0]:
            cleaned = _clean_primo_field(str(vals[0]))
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
    raw_author = _extract_primo_text(addata, "au", "creatorfull") or _extract_primo_text(display, "creator")
    raw_author = raw_author.rstrip(".").strip()
    publisher = _extract_primo_text(addata, "pub") or _extract_primo_text(display, "publisher")
    return {"isbn": isbn, "title": title, "author": raw_author or publisher, "publisher": publisher}


def _collect_lexical_texts(val: Any, texts: List[str]) -> None:
    """Collect non-empty text strings from a Lexical JSON tree in order."""
    if isinstance(val, dict):
        text = val.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
        for child in val.values():
            _collect_lexical_texts(child, texts)
    elif isinstance(val, list):
        for item in val:
            _collect_lexical_texts(item, texts)


def _find_next_text(texts: List[str], prefix: str) -> str:
    for idx, item in enumerate(texts):
        if item.startswith(prefix):
            inline = item[len(prefix):].lstrip(" :\xa0").strip()
            if inline:
                return inline
            if idx + 1 < len(texts) and not texts[idx + 1].startswith(DISALLOWED_PREFIXES):
                return texts[idx + 1]
    return ""


def _extract_seed_detail(detail_data: Optional[dict]) -> Tuple[str, str]:
    """Extract author and publisher from SE-ED physical product detail."""
    detail_str = ((detail_data or {}).get("physicalProduct") or {}).get("detail", "")
    if not isinstance(detail_str, str) or not detail_str:
        return "", ""
    try:
        texts: List[str] = []
        _collect_lexical_texts(json.loads(detail_str), texts)
        return _find_next_text(texts, "ผู้เขียน"), _find_next_text(texts, "สำนักพิมพ์")
    except Exception:
        return "", ""


def _match_seed_sku(variants: list, isbn: str) -> bool:
    """Verify at least one variant matches the normalized ISBN SKU."""
    return not variants or any(
        normalize_isbn(str(v.get("sku", ""))) == isbn for v in variants if isinstance(v, dict)
    )


def parse_seed_product(
    search_data: dict, detail_data: Optional[dict], isbn: str
) -> Optional[Dict[str, str]]:
    """Parse SE-ED search and detail responses to extract book metadata."""
    products = search_data.get("products") or []
    if not products or not isinstance(products[0], dict):
        return None
    pp = ((products[0].get("physicalProduct") or {}).get("physicalProduct") or {})
    if not _match_seed_sku(pp.get("variants") or [], isbn):
        return None
    title = str(pp.get("name") or "").strip()
    if not title:
        return None
    raw_author, publisher = _extract_seed_detail(detail_data)
    return {"isbn": isbn, "title": title, "author": raw_author or publisher, "publisher": publisher}


def parse_openlibrary_json(data: dict, isbn: str) -> Optional[Dict[str, str]]:
    """Parse Open Library book data JSON response."""
    book = data.get(f"ISBN:{isbn}")
    if not isinstance(book, dict) or not book.get("title"):
        return None
    title = str(book.get("title", "")).strip()
    authors = [a.get("name", "").strip() for a in book.get("authors", []) if isinstance(a, dict) and a.get("name")]
    pubs = [p.get("name", "").strip() for p in book.get("publishers", []) if isinstance(p, dict) and p.get("name")]
    raw_author = ", ".join(filter(None, authors))
    publisher = ", ".join(filter(None, pubs))
    return {"isbn": isbn, "title": title, "author": raw_author or publisher, "publisher": publisher}


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
        s_url = f"{SEED_SEARCH_URL}?filter.keyword={isbn}&option.limit=1&option.skip=0"
        s_data = _fetch_json(s_url, timeout)
        products = s_data.get("products") or []
        if not products or not isinstance(products[0], dict):
            return None
        pp = ((products[0].get("physicalProduct") or {}).get("physicalProduct") or {})
        prod_id = products[0].get("id") or pp.get("id")
        d_data = _fetch_seed_detail(prod_id, timeout)
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
    step_timeout = min(timeout, 2.5)
    return (
        _fetch_primo(isbn, step_timeout)
        or _fetch_seed(isbn, step_timeout)
        or _fetch_openlibrary(isbn, timeout)
    )
