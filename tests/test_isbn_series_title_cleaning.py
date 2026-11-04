"""
tests/test_isbn_series_title_cleaning.py
Reproduction and regression test suite for NLT Primo series title prepending
and parallel title cleaning (e.g. ISBN 9786160443536).
"""
import pytest
from core.library.services.isbn_providers import (
    parse_nlt_primo_json,
    fetch_remote_providers,
)
from core.library.services.primo_title_cleaner import (
    clean_parallel_title,
    clean_series_title,
    compose_primo_title,
)
from core.library.services.isbn_service import IsbnLookupService
from data.db import get_connection
from data.migrate import apply_migrations


def _build_primo_doc(btitle: str, seriestitle: str = "", display_series: str = ""):
    """Helper to build a mock NLT Primo pnx doc structure."""
    addata = {"btitle": [btitle], "au": ["Park, Myeong-suk"], "pub": ["นานมีบุ๊คส์"]}
    display = {"title": [btitle], "creator": ["Park, Myeong-suk"], "publisher": ["นานมีบุ๊คส์"]}
    if seriestitle:
        addata["seriestitle"] = [seriestitle]
    if display_series:
        display["series"] = [display_series]
    return {"docs": [{"pnx": {"addata": addata, "display": display}}]}


def test_primo_prepends_series_and_cleans_parallel_title():
    """Verify NLT Primo prepends series title and removes English parallel title."""
    doc = _build_primo_doc(
        btitle="แรงโน้มถ่วง = Gravity",
        seriestitle="เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ",
        display_series="เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ",
    )
    parsed = parse_nlt_primo_json(doc, "9786160443536")

    assert parsed is not None
    assert parsed["title"] == "เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ แรงโน้มถ่วง"


def test_primo_avoids_duplicate_series_when_already_in_title():
    """Verify series title is not prepended if already present at start of title."""
    doc = _build_primo_doc(
        btitle="เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ แรงโน้มถ่วง = Gravity",
        seriestitle="เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ",
        display_series="เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ",
    )
    parsed = parse_nlt_primo_json(doc, "9786160443536")

    assert parsed is not None
    assert parsed["title"] == "เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ แรงโน้มถ่วง"


def test_primo_cleans_parallel_title_without_series():
    """Verify parallel title '=' is cleaned when no series title exists."""
    doc_parallel = _build_primo_doc(btitle="ฟิสิกส์มหาวิทยาลัย = University Physics")
    parsed_parallel = parse_nlt_primo_json(doc_parallel, "9786160000001")
    assert parsed_parallel is not None
    assert parsed_parallel["title"] == "ฟิสิกส์มหาวิทยาลัย"

    doc_plain = _build_primo_doc(btitle="ประวัติศาสตร์อยุธยาศึกษา")
    parsed_plain = parse_nlt_primo_json(doc_plain, "9786160000002")
    assert parsed_plain is not None
    assert parsed_plain["title"] == "ประวัติศาสตร์อยุธยาศึกษา"


def test_primo_title_cleaner_unit_edge_cases():
    """Verify cleaner helpers on empty, multiple delimiters, and whitespace inputs."""
    assert clean_parallel_title("") == ""
    assert clean_parallel_title("   ") == ""
    assert clean_parallel_title(None) == ""
    assert clean_parallel_title("  วิทยาศาสตร์ ๑   = Science 1 = Book  ") == "วิทยาศาสตร์ ๑"

    assert clean_series_title("") == ""
    assert clean_series_title("   ") == ""
    assert clean_series_title(None) == ""
    assert clean_series_title("ชุด เก่งวิทย์$$vเล่ม 1 = Science Series") == "ชุด เก่งวิทย์"


def test_compose_primo_title_adversarial_combinations():
    """Verify compose_primo_title across edge cases (empty, leading/trailing space, unicode)."""
    assert compose_primo_title("", "ชุดการเรียนรู้") == ""
    assert compose_primo_title("ชีววิทยา ๒", "") == "ชีววิทยา ๒"
    assert compose_primo_title("  เคมีเบื้องต้น = Chemistry  ", "  ชุด สสวท.  ") == "ชุด สสวท. เคมีเบื้องต้น"
    assert compose_primo_title("ชุด นิทาน ๑ = Tales", "ชุด นิทาน") == "ชุด นิทาน ๑"


def test_primo_json_parser_marc_and_display_fallback():
    """Verify parser strips MARC tags from series and falls back to display.series."""
    doc_marc = {
        "docs": [{
            "pnx": {
                "addata": {"btitle": ["กลศาสตร์ = Mechanics"], "seriestitle": ["ชุด ฟิสิกส์ทฤษฎี$$vเล่ม 1"]},
                "display": {"creator": ["ศ.ดร. นิวตัน"]},
            }
        }]
    }
    res = parse_nlt_primo_json(doc_marc, "9786160000003")
    assert res is not None
    assert res["title"] == "ชุด ฟิสิกส์ทฤษฎี กลศาสตร์"

    doc_display_only = {
        "docs": [{
            "pnx": {
                "addata": {"btitle": ["คลื่นแม่เหล็กไฟฟ้า"]},
                "display": {"series": ["สารานุกรมวิทยาศาสตร์ = Science Encyclopedia"]},
            }
        }]
    }
    res_display = parse_nlt_primo_json(doc_display_only, "9786160000004")
    assert res_display is not None
    assert res_display["title"] == "สารานุกรมวิทยาศาสตร์ คลื่นแม่เหล็กไฟฟ้า"


def test_mocked_isbn_lookup_service_9786160443536(monkeypatch, tmp_path):
    """Verify IsbnLookupService produces cleaned series title for 9786160443536."""
    conn = get_connection(str(tmp_path / "isbn_test.sqlite"), pin="123456")
    apply_migrations(conn)
    svc = IsbnLookupService(conn)

    mock_doc = _build_primo_doc(
        btitle="แรงโน้มถ่วง = Gravity",
        seriestitle="เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ",
    )
    monkeypatch.setattr(
        "core.library.services.isbn_providers._fetch_json",
        lambda url, timeout=5.0: mock_doc,
    )

    result = svc.lookup("9786160443536")
    assert result.ok is True
    assert result.data["title"] == "เก่งวิทย์ด้วยตัวเองจนคุณครูตกใจ แรงโน้มถ่วง"
    conn.close()
