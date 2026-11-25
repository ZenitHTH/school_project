"""Qt QPdfWriter renderer for barcode label sheets with Unicode (Thai) book titles."""

import math
import os
from typing import Callable, List, Tuple

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QPageLayout, QPageSize, QPainter, QPdfWriter, QPen

_PAGE_W = 595.28
_PAGE_H = 841.89
_MARGIN = 24.0
_PADDING = 4.0


def _ensure_qt_app() -> None:
    if QGuiApplication.instance() is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        QGuiApplication([])


def _draw_code128_bars(
    painter: QPainter, bits: str, bc_x: float, bc_y: float, bc_w: float, bc_h: float
) -> None:
    module_w = bc_w / len(bits)
    black = QColor(0, 0, 0)
    m = 0
    total = len(bits)
    while m < total:
        if bits[m] == "1":
            start = m
            while m < total and bits[m] == "1":
                m += 1
            painter.fillRect(QRectF(bc_x + start * module_w, bc_y, (m - start) * module_w, bc_h), black)
        else:
            m += 1


def _tokenize_title(title: str) -> List[str]:
    """Segment Thai/mixed text into word tokens via PyThaiNLP newmm, with char fallback."""
    try:
        from pythainlp.tokenize import word_tokenize
        return word_tokenize(title, engine="newmm")
    except Exception:
        return list(title)


def _wrap_tokens(tokens: List[str], fm: QFontMetricsF, max_w: float, max_lines: int) -> List[str]:
    """Pack word tokens into up to max_lines; elide final line if tokens remain."""
    lines: List[str] = []
    idx = 0
    while idx < len(tokens) and len(lines) < max_lines:
        if len(lines) == max_lines - 1:
            rest = "".join(tokens[idx:]).strip()
            if rest:
                lines.append(fm.elidedText(rest, Qt.ElideRight, max_w))
            break
        cur = ""
        while idx < len(tokens):
            cand = cur + tokens[idx]
            if cur and fm.horizontalAdvance(cand.strip()) > max_w:
                break
            cur = cand
            idx += 1
        lines.append(cur.strip())
    return [ln for ln in lines if ln]


def _fit_title_lines(title: str, max_w: float, max_lines: int = 4) -> Tuple[List[str], float]:
    """Fit title into 1..4 word-wrapped lines, stepping font size down for longer titles."""
    for pt_size, limit in ((7.5, 1), (6.5, 2), (6.0, 3), (5.5, max_lines)):
        font = QFont()
        font.setPointSizeF(pt_size)
        fm = QFontMetricsF(font)
        if limit == 1 and fm.horizontalAdvance(title) <= max_w:
            return [title], pt_size
        if limit > 1:
            tokens = _tokenize_title(title)
            lines = _wrap_tokens(tokens, fm, max_w, limit)
            if len(lines) <= limit and not lines[-1].endswith("…"):
                return lines, pt_size
            if limit == max_lines:
                return lines, pt_size
    return [title], 5.5


def _draw_qt_label_cell(
    painter: QPainter,
    barcode_str: str,
    title: str,
    cell_x: float,
    cell_y: float,
    cell_w: float,
    cell_h: float,
    encode_bits: Callable[[str], str],
) -> None:
    # 1. Dashed cut guide
    pen = QPen(QColor(179, 179, 179), 0.5, Qt.DashLine)
    painter.setPen(pen)
    painter.drawRect(QRectF(cell_x + _PADDING, cell_y + _PADDING, cell_w - 2 * _PADDING, cell_h - 2 * _PADDING))

    inner_w = cell_w - 4 * _PADDING
    painter.setPen(QColor(0, 0, 0))

    # 2. Fixed top title zone (32pt tall); vertically center 1..4 wrapped lines inside it
    title_zone_y = cell_y + _PADDING + 1.5
    title_zone_h = 32.0
    if title:
        title_lines, pt_size = _fit_title_lines(title, inner_w)
        title_font = QFont()
        title_font.setPointSizeF(pt_size)
        painter.setFont(title_font)
        line_h = pt_size + 2.2
        block_h = len(title_lines) * line_h
        start_y = title_zone_y + max(0.0, (title_zone_h - block_h) / 2.0)
        for i, line in enumerate(title_lines):
            rect = QRectF(cell_x + 2 * _PADDING, start_y + i * line_h, inner_w, line_h)
            painter.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, line)

    # 3. Fixed-size Code128-B bars (uniform position and height across all labels)
    text_top = cell_y + cell_h - _PADDING - 14.0
    bc_y = title_zone_y + title_zone_h + 2.0
    bc_h = (text_top - 2.5) - bc_y
    bc_w = inner_w * 0.88
    bc_x = cell_x + (cell_w - bc_w) / 2.0
    _draw_code128_bars(painter, encode_bits(barcode_str), bc_x, bc_y, bc_w, bc_h)

    # 4. Human-readable barcode at bottom
    bc_font = QFont()
    bc_font.setPointSizeF(8.5)
    bc_font.setBold(True)
    painter.setFont(bc_font)
    text_rect = QRectF(cell_x + _PADDING, text_top, cell_w - 2 * _PADDING, 13.0)
    painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignVCenter, barcode_str)


def export_label_sheet_qt_pdf(
    items: List[Tuple[str, str]],
    output_path: str,
    cols: int,
    rows: int,
    encode_bits: Callable[[str], str],
) -> None:
    """Render A4 barcode label sheet with Unicode titles using Qt QPdfWriter."""
    _ensure_qt_app()
    writer = QPdfWriter(output_path)
    writer.setResolution(72)
    writer.setPageLayout(
        QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(0, 0, 0, 0))
    )

    cell_w = (_PAGE_W - 2.0 * _MARGIN) / cols
    cell_h = (_PAGE_H - 2.0 * _MARGIN) / rows
    per_page = cols * rows
    total_pages = math.ceil(len(items) / per_page)

    painter = QPainter(writer)
    try:
        for page_idx in range(total_pages):
            if page_idx > 0:
                writer.newPage()
            start = page_idx * per_page
            for idx in range(start, min(start + per_page, len(items))):
                pos = idx % per_page
                cell_x = _MARGIN + (pos % cols) * cell_w
                cell_y = _MARGIN + (pos // cols) * cell_h
                barcode_str, title = items[idx]
                _draw_qt_label_cell(painter, barcode_str, title, cell_x, cell_y, cell_w, cell_h, encode_bits)
    finally:
        painter.end()
