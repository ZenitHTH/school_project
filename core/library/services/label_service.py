"""Pure-stdlib Code128-B barcode and PDF 1.4 label sheet generator.

Zero external dependencies (no python-barcode, Pillow, or reportlab required).
ISO/IEC 15417 Code 128 character set B + Vector PDF 1.4 generator.
"""

import math
from typing import List, Tuple, Union

# ISO/IEC 15417 Code 128 patterns (0..106)
# Each pattern is an 11-module bit pattern (except stop pattern 106 which has 13 modules).
_CODE128_PATTERNS = (
    "11011001100", "11001101100", "11001100110", "10010011000", "10010001100",
    "10001001100", "10011001000", "10011000100", "10001100100", "11001001000",
    "11001000100", "11000100100", "10110011100", "10011011100", "10011001110",
    "10111001100", "10011101100", "10011100110", "11001110010", "11001011100",
    "11001001110", "11011100100", "11001110100", "11101101110", "11101001100",
    "11100101100", "11100100110", "11101100100", "11100110100", "11100110010",
    "11011011000", "11011000110", "11000110110", "10100011000", "10001011000",
    "10001000110", "10110001000", "10001101000", "10001100010", "11010001000",
    "11000101000", "11000100010", "10110111000", "10110001110", "10001101110",
    "10111011000", "10111000110", "10001110110", "11101110110", "11010001110",
    "11000101110", "11011101000", "11011100010", "11011101110", "11101011000",
    "11101000110", "11100010110", "11101101000", "11101100010", "11100011010",
    "11101111010", "11001000010", "11110001010", "10100110000", "10100001100",
    "10010110000", "10010000110", "10000101100", "10000100110", "10110010000",
    "10110000100", "10011010000", "10011000010", "10000110100", "10000110010",
    "11000010010", "11001010000", "11110111010", "11000010100", "10001111010",
    "10100111100", "10010111100", "10010011110", "10111100100", "10011110100",
    "10011110010", "11110100100", "11110010100", "11110010010", "11011011110",
    "11011110110", "11110110110", "10101111000", "10100011110", "10001011110",
    "10111101000", "10111100010", "11110101000", "11110100010", "10111011110",
    "10111101110", "11101011110", "11110101110", "11010000100", "11010010000",
    "11010011100", "1100011101011",
)

# Standard Helvetica-Bold character widths (units per 1000 em)
_HELVETICA_BOLD_WIDTHS = {
    " ": 278, "!": 333, '"': 474, "#": 556, "$": 556, "%": 889, "&": 722, "'": 278,
    "(": 389, ")": 389, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556, "7": 556,
    "8": 556, "9": 556, ":": 333, ";": 333, "<": 584, "=": 584, ">": 584, "?": 556,
    "@": 975, "A": 722, "B": 722, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 778, "I": 278, "J": 556, "K": 722, "L": 611, "M": 833, "N": 722, "O": 778,
    "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944,
    "X": 667, "Y": 667, "Z": 611, "[": 389, "\\": 278, "]": 389, "^": 584, "_": 556,
    "`": 333, "a": 556, "b": 611, "c": 556, "d": 611, "e": 556, "f": 333, "g": 611,
    "h": 611, "i": 278, "j": 278, "k": 556, "l": 278, "m": 889, "n": 611, "o": 611,
    "p": 611, "q": 611, "r": 389, "s": 556, "t": 333, "u": 611, "v": 556, "w": 778,
    "x": 556, "y": 556, "z": 500, "{": 389, "|": 280, "}": 389, "~": 584,
}


def _encode_code128_b_bits(text: str) -> str:
    """Encode ASCII string into Code128-B module bit pattern (1=bar, 0=space)."""
    vals: List[int] = []
    for ch in text:
        code = ord(ch)
        if 32 <= code <= 126:
            vals.append(code - 32)
        else:
            vals.append(ord("?") - 32)

    # Start B = 104
    start_code = 104
    weighted_sum = start_code + sum((i + 1) * val for i, val in enumerate(vals))
    checksum = weighted_sum % 103

    symbols = [start_code] + vals + [checksum, 106]
    return "".join(_CODE128_PATTERNS[s] for s in symbols)


def _escape_pdf_literal(text: str) -> Tuple[str, float]:
    """Escape string for PDF literal text (...) and compute text width at 9pt."""
    escaped_chars: List[str] = []
    total_width_units = 0.0
    for ch in text:
        code = ord(ch)
        if ch in ("\\", "(", ")"):
            escaped_chars.append("\\" + ch)
            total_width_units += _HELVETICA_BOLD_WIDTHS.get(ch, 556)
        elif 32 <= code <= 126:
            escaped_chars.append(ch)
            total_width_units += _HELVETICA_BOLD_WIDTHS.get(ch, 556)
        else:
            escaped_chars.append("?")
            total_width_units += _HELVETICA_BOLD_WIDTHS.get("?", 556)

    width_pt = total_width_units * (9.0 / 1000.0)
    return "".join(escaped_chars), width_pt


def export_label_sheet_pdf(
    copies: List[Union[Tuple[int, str], str]],
    output_path: str,
    cols: int = 3,
    rows: int = 8,
) -> None:
    """
    Export a printable A4 PDF containing barcode labels arranged in a grid with dashed cut guides.
    copies: list of tuples (copy_id, barcode_str) or list of barcode strings.
    """
    if not copies:
        raise ValueError("No copies provided to export")

    barcode_items: List[str] = []
    for item in copies:
        if isinstance(item, tuple):
            barcode_items.append(str(item[1]).strip())
        else:
            barcode_items.append(str(item).strip())

    page_width = 595.28  # A4 width in pt
    page_height = 841.89  # A4 height in pt
    margin_x = 24.0
    margin_y = 24.0

    usable_width = page_width - (2.0 * margin_x)
    usable_height = page_height - (2.0 * margin_y)

    cell_width = usable_width / cols
    cell_height = usable_height / rows
    cell_padding = 4.0

    items_per_page = cols * rows
    total_pages = math.ceil(len(barcode_items) / items_per_page)

    page_streams: List[bytes] = []

    for page_idx in range(total_pages):
        stream_lines: List[str] = []
        start_item_idx = page_idx * items_per_page
        end_item_idx = min(start_item_idx + items_per_page, len(barcode_items))

        for idx in range(start_item_idx, end_item_idx):
            barcode_str = barcode_items[idx]
            pos_on_page = idx % items_per_page
            col = pos_on_page % cols
            row = pos_on_page // cols

            cell_x = margin_x + (col * cell_width)
            cell_y = page_height - margin_y - ((row + 1) * cell_height)

            # 1. Dashed cut guide box
            gx = cell_x + cell_padding
            gy = cell_y + cell_padding
            gw = cell_width - (2.0 * cell_padding)
            gh = cell_height - (2.0 * cell_padding)
            stream_lines.append(
                f"q 0.7 0.7 0.7 RG 0.5 w [3 3] 0 d {gx:.2f} {gy:.2f} {gw:.2f} {gh:.2f} re S Q"
            )

            # 2. Vector barcode rectangles
            bits = _encode_code128_b_bits(barcode_str)
            total_modules = len(bits)

            inner_w = cell_width - (4.0 * cell_padding)
            inner_h = cell_height - (4.0 * cell_padding)

            bc_img_w = inner_w * 0.88
            bc_img_h = inner_h * 0.55
            bc_x = cell_x + (cell_width - bc_img_w) / 2.0
            bc_y = cell_y + cell_padding + (inner_h * 0.35)

            module_w = bc_img_w / total_modules

            stream_lines.append("q 0 0 0 rg")
            m = 0
            while m < total_modules:
                if bits[m] == "1":
                    run_start = m
                    while m < total_modules and bits[m] == "1":
                        m += 1
                    run_len = m - run_start
                    bx = bc_x + (run_start * module_w)
                    bw = run_len * module_w
                    stream_lines.append(f"{bx:.2f} {bc_y:.2f} {bw:.2f} {bc_img_h:.2f} re f")
                else:
                    m += 1
            stream_lines.append("Q")

            # 3. Human-readable barcode text
            escaped_text, text_width = _escape_pdf_literal(barcode_str)
            text_x = cell_x + (cell_width - text_width) / 2.0
            text_y = cell_y + cell_padding + 6.0
            stream_lines.append(
                f"BT /F1 9 Tf {text_x:.2f} {text_y:.2f} Td ({escaped_text}) Tj ET"
            )

        page_streams.append("\n".join(stream_lines).encode("latin1"))

    # Assemble PDF 1.4 document
    num_pages = len(page_streams)
    font_id = 3 + 2 * num_pages
    total_objs = font_id

    out = bytearray()
    out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (total_objs + 1)

    def write_obj(num: int, body: bytes) -> None:
        offsets[num] = len(out)
        out.extend(f"{num} 0 obj\n".encode("ascii"))
        out.extend(body)
        out.extend(b"\nendobj\n")

    # 1: Catalog
    write_obj(1, b"<<\n  /Type /Catalog\n  /Pages 2 0 R\n>>")

    # 2: Pages
    kids_str = " ".join(f"{3 + 2 * i} 0 R" for i in range(num_pages))
    write_obj(2, f"<<\n  /Type /Pages\n  /Kids [{kids_str}]\n  /Count {num_pages}\n>>".encode("ascii"))

    for i, stream in enumerate(page_streams):
        page_id = 3 + 2 * i
        content_id = 4 + 2 * i
        page_body = (
            f"<<\n  /Type /Page\n  /Parent 2 0 R\n  /MediaBox [0 0 {page_width:.2f} {page_height:.2f}]\n"
            f"  /Contents {content_id} 0 R\n  /Resources <<\n    /Font << /F1 {font_id} 0 R >>\n  >>\n>>"
        ).encode("ascii")
        write_obj(page_id, page_body)

        content_body = f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"
        write_obj(content_id, content_body)

    # Font object
    write_obj(font_id, b"<<\n  /Type /Font\n  /Subtype /Type1\n  /BaseFont /Helvetica-Bold\n>>")

    xref_offset = len(out)
    out.extend(f"xref\n0 {total_objs + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for num in range(1, total_objs + 1):
        out.extend(f"{offsets[num]:010d} 00000 n \n".encode("ascii"))

    out.extend(
        f"trailer\n<<\n  /Size {total_objs + 1}\n  /Root 1 0 R\n>>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )

    with open(output_path, "wb") as f:
        f.write(out)
