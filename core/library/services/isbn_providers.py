"""Remote ISBN metadata providers: NLT Primo VE, SE-ED BFF, Open Library, Chulabook, and Nain Book."""

import html
import json
import logging
import re
import ssl
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

logger = logging.getLogger("smte.isbn")

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
from core.library.services.primo_title_cleaner import compose_primo_title

NLT_PRIMO_URL = "https://nlt.primo.exlibrisgroup.com/primaws/rest/pub/pnxs"
SEED_SEARCH_URL = "https://mp-api.se-ed.com/web-bff/search-product"
SEED_DETAIL_URL = "https://mp-api.se-ed.com/web-bff/physical-product"
OPENLIBRARY_URL = "https://openlibrary.org/api/books"
CHULABOOK_API = "https://api.chulabook.com"
CHULABOOK_HEADERS = {"Origin": "https://www.chulabook.com", "Referer": "https://www.chulabook.com/"}
NAIIN_BASE = "https://www.naiin.com"
NAIIN_HEADERS = {
    "Referer": "https://www.naiin.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
UNKNOWN_PUBS = ("-ไม่ปรากฏสำนักพิมพ์", "ไม่ปรากฏสำนักพิมพ์", "ม.ป.พ.", "ม.ป.ท.")

__all__ = [
    "normalize_isbn",
    "is_valid_isbn",
    "is_arabic_isbn",
    "CHULABOOK_API",
    "CHULABOOK_HEADERS",
    "parse_chulabook_products",
    "parse_chulabook_detail",
    "_fetch_chulabook",
    "NAIIN_BASE",
    "NAIIN_HEADERS",
    "parse_nain_search_items",
    "parse_nain_product_ld",
    "_fetch_nain",
    "_fetch_text",
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


def _fetch_json(url: str, timeout: float = 5.0, extra_headers: Optional[dict] = None) -> dict:
    """Fetch JSON from URL with User-Agent header and default SSL context."""
    headers = {"User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            data = json.loads(resp.read().decode(charset, errors="replace"))
    except Exception as exc:
        logger.warning(
            "http GET %s failed after %.2fs (timeout=%.1fs): %s: %s",
            url, time.monotonic() - t0, timeout, type(exc).__name__, exc,
        )
        raise
    logger.debug("http GET %s -> %s in %.2fs", url, getattr(resp, "status", "?"), time.monotonic() - t0)
    return data


def _fetch_text(url: str, timeout: float = 5.0, extra_headers: Optional[dict] = None) -> Optional[str]:
    """Fetch HTML/text from URL with the standard User-Agent; returns decoded body or None on failure."""
    headers = {"User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset, errors="replace")
    except Exception as exc:
        logger.warning(
            "http GET %s failed after %.2fs (timeout=%.1fs): %s: %s",
            url, time.monotonic() - t0, timeout, type(exc).__name__, exc,
        )
        return None
    logger.debug("http GET %s -> text in %.2fs", url, time.monotonic() - t0)
    return body


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
    raw_title = _extract_primo_text(addata, "btitle") or _extract_primo_text(display, "title")
    raw_series = _extract_primo_text(addata, "seriestitle") or _extract_primo_text(display, "series")
    title = compose_primo_title(raw_title, raw_series)
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


def parse_chulabook_products(data: dict, isbn: str) -> Optional[str]:
    """Return the product id of the first row whose barcode exactly matches the ISBN (normalized)."""
    target = normalize_isbn(isbn)
    for row in data.get("rows") or []:
        if isinstance(row, dict) and normalize_isbn(str(row.get("barcode") or "")) == target:
            return str(row.get("id"))
    return None


def parse_chulabook_detail(data: dict, isbn: str) -> Optional[Dict[str, str]]:
    """Map a Chulabook product detail record to the standard metadata dict (no publisher-name field exists in the API)."""
    name = data.get("name")
    if not name:
        return None
    return {
        "isbn": isbn,
        "title": str(name).strip(),
        "author": str(data.get("author") or data.get("translator") or "").strip(),
        "publisher": "",
    }


def _fetch_chulabook(isbn: str, timeout: float) -> Optional[Dict[str, str]]:
    """Chulabook store API: exact-barcode search then product detail.

    5 s timeout per request (spec §4.6) with one retry per request —
    slow school networks made the old 2.5 s step time out on the first
    cold TLS handshake, which looked like "chulabook cannot fetch".
    """
    step = min(timeout, 5.0)

    def _get(url: str) -> Optional[dict]:
        for attempt in range(2):
            try:
                return _fetch_json(url, timeout=step, extra_headers=CHULABOOK_HEADERS)
            except Exception as exc:
                if attempt == 0:
                    logger.warning("chulabook %s failed (attempt 1): %s: %s — retrying in 0.5s", url, type(exc).__name__, exc)
                    time.sleep(0.5)
                else:
                    logger.warning("chulabook %s failed (attempt 2): %s: %s", url, type(exc).__name__, exc)
        return None

    try:
        data = _get(f"{CHULABOOK_API}/products?search={isbn}&limit=5")
        if not data:
            logger.debug("chulabook search for %s failed after retry, skip", isbn)
            return None
        rows = data.get("rows") or []
        logger.debug("chulabook search %s: %d row(s) returned", isbn, len(rows))
        pid = parse_chulabook_products(data, isbn)
        if not pid:
            logger.debug("chulabook search %s: no exact barcode match, skip", isbn)
            return None
        detail = _get(f"{CHULABOOK_API}/products/{pid}")
        if not detail:
            logger.debug("chulabook detail %s (id=%s) failed after retry, skip", isbn, pid)
            return None
        meta = parse_chulabook_detail(detail, isbn)
        logger.debug("chulabook detail %s (id=%s) -> %s", isbn, pid, meta["title"] if meta else "unparseable")
        return meta
    except Exception as exc:
        logger.warning("chulabook fetch %s error: %s: %s", isbn, type(exc).__name__, exc)
        return None


NAIIN_ITEMS_RE = re.compile(r"<product-list[^>]*?:items='(.*?)'\s*:default-error=", re.S)
NAIIN_LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def parse_nain_search_items(html_text: str) -> List[dict]:
    """Extract the product JSON array embedded in a /search-result page.

    The SSR page renders ``<product-list :items='[...]' :default-error='null'>``
    with a JSON array (HTML-entity-escaped for single quotes) of product rows
    carrying ProductID / ProductName / AuthorName / PublisherName / prices.
    """
    m = NAIIN_ITEMS_RE.search(html_text)
    if not m:
        return []
    try:
        items = json.loads(html.unescape(m.group(1)))
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(items, list):
        return []
    return [it for it in items if isinstance(it, dict) and it.get("ProductID")]


def _nain_ld_name(value) -> str:
    """Resolve a schema.org field that may be a string, a dict with name, or a list of either."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("name") or "").strip()
    if isinstance(value, list):
        return ", ".join(n for n in (_nain_ld_name(v) for v in value) if n)
    return ""


def parse_nain_product_ld(html_text: str, isbn: str) -> Optional[Dict[str, str]]:
    """Parse the schema.org Product/Book JSON-LD block from a /product/detail page.

    Returns the standard metadata dict only when the block's ISBN (``isbn`` or
    ``gtin13``/``sku``) exactly matches the queried ISBN (normalized).
    """
    target = normalize_isbn(isbn)
    for block in NAIIN_LD_RE.findall(html_text):
        try:
            data = json.loads(block)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        block_types = data.get("@type") or []
        if isinstance(block_types, str):
            block_types = [block_types]
        if "Book" not in block_types and "Product" not in block_types:
            continue
        block_isbn = next(
            (normalize_isbn(str(data[k])) for k in ("isbn", "gtin13", "sku") if data.get(k)),
            "",
        )
        if block_isbn and block_isbn != target:
            continue
        title = str(data.get("name") or "").strip()
        if not title:
            continue
        brand = data.get("brand")
        return {
            "isbn": isbn,
            "title": title,
            "author": _nain_ld_name(data.get("author")),
            "publisher": _nain_ld_name(data.get("publisher")) or _nain_ld_name(brand),
        }
    return None


def _fetch_nain(isbn: str, timeout: float) -> Optional[Dict[str, str]]:
    """Nain Book (naiin.com) store: ISBN search on /search-result, then JSON-LD from /product/detail.

    Two steps like Chulabook: the search page embeds a product JSON array
    (no ISBN field), so each candidate's detail page is fetched and its
    schema.org JSON-LD matched against the queried ISBN. Same 5 s per-request
    budget and one retry per request as the Chulabook provider.
    """
    step = min(timeout, 5.0)

    def _get(url: str) -> Optional[str]:
        for attempt in range(2):
            body = _fetch_text(url, timeout=step, extra_headers=NAIIN_HEADERS)
            if body is not None:
                return body
            if attempt == 0:
                logger.warning("nain GET %s failed (attempt 1) — retrying in 0.5s", url)
                time.sleep(0.5)
            else:
                logger.warning("nain GET %s failed (attempt 2)", url)
        return None

    try:
        page = _get(f"{NAIIN_BASE}/search-result?title={urllib.parse.quote(isbn)}")
        if not page:
            logger.debug("nain search for %s failed after retry, skip", isbn)
            return None
        items = parse_nain_search_items(page)
        if not items:
            logger.debug("nain search %s: no product items in page, skip", isbn)
            return None
        candidates = items[:3]
        for it in candidates:
            pid = it.get("ProductID")
            detail = _get(f"{NAIIN_BASE}/product/detail/{pid}")
            if not detail:
                logger.debug("nain detail %s (ProductID=%s) failed after retry, skip", isbn, pid)
                continue
            meta = parse_nain_product_ld(detail, isbn)
            if meta:
                if not meta["author"]:
                    meta["author"] = str(it.get("AuthorName") or "").strip()
                if not meta["publisher"]:
                    meta["publisher"] = str(it.get("PublisherName") or "").strip()
                logger.debug("nain detail %s (ProductID=%s) -> %s", isbn, pid, meta["title"])
                return meta
            logger.debug("nain detail %s (ProductID=%s): no exact ISBN in JSON-LD", isbn, pid)
        logger.debug("nain search %s: %d candidate(s) checked, no exact ISBN match, skip", isbn, len(candidates))
        return None
    except Exception as exc:
        logger.warning("nain fetch %s error: %s: %s", isbn, type(exc).__name__, exc)
        return None


def _fetch_primo(isbn: str, timeout: float) -> Optional[Dict[str, str]]:
    try:
        url = f"{NLT_PRIMO_URL}?vid=66NLT_INST:66NLT&q=isbn,exact,{isbn}&offset=0&limit=1&lang=th"
        data = _fetch_json(url, timeout)
        meta = parse_nlt_primo_json(data, isbn)
        if not meta:
            logger.debug("NLT Primo %s: response had no usable docs/title", isbn)
        return meta
    except Exception as exc:
        logger.warning("NLT Primo %s error: %s: %s", isbn, type(exc).__name__, exc)
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
            logger.debug("SE-ED %s: no product in search response", isbn)
            return None
        pp = ((prods[0].get("physicalProduct") or {}).get("physicalProduct") or {})
        d_data = _fetch_seed_detail(prods[0].get("id") or pp.get("id"), timeout)
        meta = parse_seed_product(s_data, d_data, isbn)
        if not meta:
            logger.debug("SE-ED %s: sku/title mismatch after detail fetch", isbn)
        return meta
    except Exception as exc:
        logger.warning("SE-ED %s error: %s: %s", isbn, type(exc).__name__, exc)
        return None


def _fetch_openlibrary(isbn: str, timeout: float) -> Optional[Dict[str, str]]:
    try:
        url = f"{OPENLIBRARY_URL}?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        data = _fetch_json(url, timeout)
        meta = parse_openlibrary_json(data, isbn)
        if not meta:
            logger.debug("Open Library %s: no book record in response", isbn)
        return meta
    except Exception as exc:
        logger.warning("Open Library %s error: %s: %s", isbn, type(exc).__name__, exc)
        return None


def fetch_remote_providers(isbn: str, timeout: float = 5.0) -> Optional[Dict[str, str]]:
    """Chain remote JSON providers: NLT Primo VE -> SE-ED BFF -> Open Library -> Chulabook -> Nain Book."""
    step = min(timeout, 2.5)
    chain = (
        ("NLT Primo", _fetch_primo, step),
        ("SE-ED", _fetch_seed, step),
        ("Open Library", _fetch_openlibrary, timeout),
        ("Chulabook", _fetch_chulabook, timeout),
        ("Nain Book", _fetch_nain, timeout),
    )
    t0 = time.monotonic()
    for name, fetch, budget in chain:
        start = time.monotonic()
        try:
            meta = fetch(isbn, budget)
        except Exception as exc:  # defensive: providers already catch their own errors
            logger.warning("provider %s raised: %s: %s", name, type(exc).__name__, exc)
            meta = None
        if meta:
            logger.info(
                "isbn %s HIT at %s after %.2fs (%.2fs total) — title=%r",
                isbn, name, time.monotonic() - start, time.monotonic() - t0, meta.get("title", ""),
            )
            return meta
        logger.info("isbn %s miss at %s after %.2fs", isbn, name, time.monotonic() - start)
    logger.info("isbn %s not found by any remote provider (%.2fs total)", isbn, time.monotonic() - t0)
    return None
