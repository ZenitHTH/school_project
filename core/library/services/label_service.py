import io
from typing import List, Tuple, Union
import barcode
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


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

    page_width, page_height = A4
    margin_x = 24.0
    margin_y = 24.0

    usable_width = page_width - (2 * margin_x)
    usable_height = page_height - (2 * margin_y)

    cell_width = usable_width / cols
    cell_height = usable_height / rows
    cell_padding = 4.0

    c = canvas.Canvas(output_path, pagesize=A4)
    code128_cls = barcode.get_barcode_class("code128")

    items_per_page = cols * rows
    total_items = len(barcode_items)

    for idx, barcode_str in enumerate(barcode_items):
        pos_on_page = idx % items_per_page
        if idx > 0 and pos_on_page == 0:
            c.showPage()

        col = pos_on_page % cols
        row = pos_on_page // cols

        # Calculate cell coordinates (origin is bottom-left in PDF)
        cell_x = margin_x + (col * cell_width)
        cell_y = page_height - margin_y - ((row + 1) * cell_height)

        # Draw dashed cut guide box
        c.saveState()
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.setLineWidth(0.5)
        c.setDash(3, 3)
        c.rect(
            cell_x + cell_padding,
            cell_y + cell_padding,
            cell_width - (2 * cell_padding),
            cell_height - (2 * cell_padding),
        )
        c.restoreState()

        # Render barcode image to buffer
        img_buffer = io.BytesIO()
        bc = code128_cls(barcode_str, writer=ImageWriter())
        bc.write(img_buffer, options={"write_text": False, "quiet_zone": 1.0})
        img_buffer.seek(0)
        img_reader = ImageReader(img_buffer)

        # Dimensions inside cell
        inner_w = cell_width - (4 * cell_padding)
        inner_h = cell_height - (4 * cell_padding)

        bc_img_w = inner_w * 0.88
        bc_img_h = inner_h * 0.55
        bc_x = cell_x + (cell_width - bc_img_w) / 2.0
        bc_y = cell_y + cell_padding + (inner_h * 0.35)

        c.drawImage(img_reader, bc_x, bc_y, width=bc_img_w, height=bc_img_h, mask="auto")

        # Draw human-readable barcode text
        c.saveState()
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(
            cell_x + (cell_width / 2.0),
            cell_y + cell_padding + 6.0,
            barcode_str,
        )
        c.restoreState()

    c.save()
