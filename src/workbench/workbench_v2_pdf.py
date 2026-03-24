"""
Construction drawing PDF for workbench_v2.

Run with:
    uv run python src/workbench/workbench_v2_pdf.py

Outputs: src/workbench/workbench_v2_construction.pdf
"""

import sys
import tempfile
from pathlib import Path

import cadquery as cq
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from workbench.workbench_v2 import make_workbench, TABLE_LENGTH, TABLE_WIDTH, LEG_HEIGHT, TABLE_THICKNESS

OUTPUT_DIR = Path(__file__).parent
PAGE_W, PAGE_H = landscape(A3)
MARGIN = 15 * mm
TITLE_H = 18 * mm   # height of title block at bottom
DRAW_H = PAGE_H - MARGIN * 2 - TITLE_H   # usable height
DRAW_W = PAGE_W - MARGIN * 2             # usable width


def rotated(shape, axis, angle):
    return shape.rotate((0, 0, 0), axis, angle)


def export_temp_svg(compound, view_name, width=1600, height=1000):
    """Export a CadQuery compound to a temp SVG file, return path."""
    tmp = tempfile.NamedTemporaryFile(suffix=f"_{view_name}.svg", delete=False)
    cq.exporters.export(
        compound,
        tmp.name,
        opt={
            "projectionDir": (0, 0, 1),
            "width": width,
            "height": height,
            "showAxes": False,
            "strokeColor": (40, 40, 40),
            "hiddenColor": (180, 180, 180),
            "showHidden": True,
        },
    )
    return Path(tmp.name)


def svg_to_rl(svg_path, target_w, target_h):
    """Convert SVG file to a scaled reportlab Drawing."""
    drawing = svg2rlg(str(svg_path))
    if drawing is None:
        return None
    scale_x = target_w / drawing.width
    scale_y = target_h / drawing.height
    scale = min(scale_x, scale_y)
    drawing.width = drawing.width * scale
    drawing.height = drawing.height * scale
    drawing.transform = (scale, 0, 0, scale, 0, 0)
    return drawing


def draw_title_block(c, page_num, total_pages, title):
    """Draw a simple title block at the bottom of the page."""
    bx = MARGIN
    by = MARGIN
    bw = DRAW_W
    bh = TITLE_H
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(bx, by, bw, bh)
    # Dividers
    c.line(bx + bw * 0.5, by, bx + bw * 0.5, by + bh)
    c.line(bx + bw * 0.75, by, bx + bw * 0.75, by + bh)
    c.line(bx + bw * 0.875, by, bx + bw * 0.875, by + bh)
    # Text
    c.setFont("Helvetica-Bold", 10)
    c.drawString(bx + 4, by + bh / 2 + 1, "Dennis Bakhuis — Workshop Workbench v2")
    c.setFont("Helvetica", 9)
    c.drawString(bx + bw * 0.5 + 4, by + bh / 2 + 1, title)
    c.drawString(bx + bw * 0.75 + 4, by + bh / 2 + 1, "Scale: NTS")
    c.drawString(bx + bw * 0.875 + 4, by + bh / 2 + 1, f"Sheet {page_num} of {total_pages}")


def draw_dim(c, x1, y1, x2, y2, text, offset=8 * mm, vertical=False):
    """Draw a simple dimension line with text."""
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor("#444444"))
    c.setFillColor(colors.black)
    if not vertical:
        # Horizontal dimension
        c.line(x1, y1 - offset, x2, y1 - offset)
        c.line(x1, y1, x1, y1 - offset - 3 * mm)
        c.line(x2, y2, x2, y2 - offset - 3 * mm)
        c.setFont("Helvetica", 7)
        c.drawCentredString((x1 + x2) / 2, y1 - offset - 4 * mm, text)
    else:
        # Vertical dimension
        c.line(x1 - offset, y1, x1 - offset, y2)
        c.line(x1, y1, x1 - offset - 3 * mm, y1)
        c.line(x2, y2, x2 - offset - 3 * mm, y2)
        c.setFont("Helvetica", 7)
        c.saveState()
        c.translate(x1 - offset - 5 * mm, (y1 + y2) / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, text)
        c.restoreState()


def place_drawing(c, rl_drawing, area_x, area_y, area_w, area_h, label):
    """Place a reportlab drawing centred in an area, with a label."""
    if rl_drawing is None:
        c.setFont("Helvetica", 9)
        c.drawCentredString(area_x + area_w / 2, area_y + area_h / 2, "[view unavailable]")
    else:
        dw, dh = rl_drawing.width, rl_drawing.height
        ox = area_x + (area_w - dw) / 2
        oy = area_y + (area_h - dh) / 2
        c.saveState()
        c.translate(ox, oy)
        renderPDF.draw(rl_drawing, c, 0, 0)
        c.restoreState()
    # Area border
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.rect(area_x, area_y, area_w, area_h)
    # Label
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawCentredString(area_x + area_w / 2, area_y + 3 * mm, label)


def main():
    print("Building workbench model...")
    workbench = make_workbench(include_props=False)
    compound = workbench.toCompound()

    # Generate all view compounds
    front_comp = rotated(compound, (-1, 0, 0), 90)
    side_comp = rotated(front_comp, (0, -1, 0), 90)
    iso_comp = rotated(rotated(compound, (-1, 0, 0), 65), (0, 1, 0), -35)

    svg_w, svg_h = 1800, 1000

    # Export SVGs
    print("Exporting SVG views...")
    top_svg = export_temp_svg(compound, "top", svg_w, svg_h)
    front_svg = export_temp_svg(front_comp, "front", svg_w, svg_h)
    side_svg = export_temp_svg(side_comp, "side", svg_h, svg_h)
    iso_svg = export_temp_svg(iso_comp, "iso", svg_w, svg_h)

    out_path = OUTPUT_DIR / "workbench_v2_construction.pdf"
    c = canvas.Canvas(str(out_path), pagesize=landscape(A3))

    content_y = MARGIN + TITLE_H + 4 * mm  # bottom of content area
    content_h = PAGE_H - content_y - MARGIN
    half_w = DRAW_W / 2 - 2 * mm

    # ── Page 1: Front + Side elevations ─────────────────────────────────
    print("Rendering page 1: Elevations...")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "ELEVATIONS")

    front_rl = svg_to_rl(front_svg, half_w - 4 * mm, content_h - 14 * mm)
    side_rl = svg_to_rl(side_svg, half_w - 4 * mm, content_h - 14 * mm)

    place_drawing(c, front_rl, MARGIN, content_y + 10 * mm, half_w, content_h - 10 * mm, "FRONT ELEVATION")
    place_drawing(c, side_rl, MARGIN + half_w + 4 * mm, content_y + 10 * mm, half_w, content_h - 10 * mm, "RIGHT SIDE ELEVATION")

    draw_title_block(c, 1, 3, "Elevations — Front & Right Side")
    c.showPage()

    # ── Page 2: Top plan + Isometric ────────────────────────────────────
    print("Rendering page 2: Plan & Isometric...")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "PLAN & 3D VIEW")

    top_rl = svg_to_rl(top_svg, half_w - 4 * mm, content_h - 14 * mm)
    iso_rl = svg_to_rl(iso_svg, half_w - 4 * mm, content_h - 14 * mm)

    place_drawing(c, top_rl, MARGIN, content_y + 10 * mm, half_w, content_h - 10 * mm, "TOP PLAN")
    place_drawing(c, iso_rl, MARGIN + half_w + 4 * mm, content_y + 10 * mm, half_w, content_h - 10 * mm, "ISOMETRIC VIEW")

    draw_title_block(c, 2, 3, "Plan & Isometric")
    c.showPage()

    # ── Page 3: Key dimensions & join details ────────────────────────────
    print("Rendering page 3: Dimensions & Construction Details...")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "DIMENSIONS & CONSTRUCTION DETAILS")

    # Key dimensions table
    dims = [
        ("Overall length", f"{TABLE_LENGTH} mm"),
        ("Overall width (main)", f"{TABLE_WIDTH} mm"),
        ("Extension depth", "200 mm"),
        ("Total depth (main + ext)", f"{TABLE_WIDTH + 200} mm"),
        ("Leg height", f"{LEG_HEIGHT} mm"),
        ("Tabletop thickness", f"{TABLE_THICKNESS} mm"),
        ("Overall height", f"{LEG_HEIGHT + TABLE_THICKNESS} mm"),
        ("Legs", "75 \u00d7 75 mm solid timber"),
        ("Stretchers", "50 \u00d7 75 mm timber (at 150 mm from floor)"),
        ("Aprons", "50 \u00d7 75 mm timber (at 885 mm from floor)"),
        ("Wall beam", "75 \u00d7 75 mm timber, wall-anchored"),
        ("Slats", "20 \u00d7 15 mm timber, 10 mm gaps"),
        ("Tabletop", "40 mm solid timber or 40 mm engineered board"),
    ]

    tx = MARGIN + 4 * mm
    ty = content_y + content_h - 6 * mm
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.black)
    c.drawString(tx, ty, "KEY DIMENSIONS & MATERIALS")
    ty -= 6 * mm
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.black)
    c.line(tx, ty, tx + 120 * mm, ty)
    ty -= 5 * mm

    for label, value in dims:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.black)
        c.drawString(tx, ty, label + ":")
        c.setFont("Helvetica", 8)
        c.drawString(tx + 60 * mm, ty, value)
        ty -= 5 * mm

    # Join details
    tx2 = MARGIN + DRAW_W / 2 + 4 * mm
    ty2 = content_y + content_h - 6 * mm

    join_details = [
        (
            "1. LEG TO APRON & STRETCHER",
            [
                "Use 2\u00d7 pocket screws (50 mm) per joint.",
                "Apron sits flush with leg inner face.",
                "Stretcher at 150 mm from floor (centre).",
                "Apron at 885 mm from floor (centre).",
                "Pre-drill and countersink to avoid splitting.",
            ],
        ),
        (
            "2. WALL BEAM TO WALL",
            [
                "75 \u00d7 75 mm timber beam, full table length.",
                "Fix with M10 \u00d7 120 mm lag screws into masonry,",
                "  or M10 bolts through stud wall at 600 mm spacing.",
                "Use rawlplugs / expansion anchors for masonry.",
                "Beam sits at apron height (885 mm from floor).",
                "Table back apron bolts to face of wall beam.",
            ],
        ),
        (
            "3. SLAT WALL MOUNTING",
            [
                "Two horizontal mounting rails per slat wall:",
                "  bottom rail at 150 mm, top rail at 885 mm from floor.",
                "Rails flush with inner face of bounding legs.",
                "Slats (20 \u00d7 15 mm) fixed with 2\u00d7 3.5 \u00d7 35 mm",
                "  wood screws per rail — top and bottom.",
                "Slats float 10 mm above floor and 10 mm below top.",
                "10 mm gap between slats (decorative / ventilation).",
            ],
        ),
        (
            "4. TABLETOP",
            [
                "Tabletop screwed down through apron top edge.",
                "Use figure-8 clips or pocket screws for wood movement.",
                "Alternatively: dominos / biscuits for panel glue-up.",
            ],
        ),
    ]

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.black)
    c.drawString(tx2, ty2, "CONSTRUCTION NOTES \u2014 JOINTS & FIXING")
    ty2 -= 6 * mm
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.black)
    c.line(tx2, ty2, tx2 + 120 * mm, ty2)
    ty2 -= 5 * mm

    for title_text, lines in join_details:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.black)
        c.drawString(tx2, ty2, title_text)
        ty2 -= 5 * mm
        c.setFont("Helvetica", 7.5)
        for line in lines:
            c.drawString(tx2 + 3 * mm, ty2, line)
            ty2 -= 4.5 * mm
        ty2 -= 3 * mm

    # Vertical divider between the two columns
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.line(MARGIN + DRAW_W / 2, content_y + 10 * mm, MARGIN + DRAW_W / 2, content_y + content_h)

    draw_title_block(c, 3, 3, "Dimensions & Construction Details")
    c.showPage()

    c.save()
    print(f"PDF saved: {out_path}")

    # Cleanup temp SVGs
    for p in [top_svg, front_svg, side_svg, iso_svg]:
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
