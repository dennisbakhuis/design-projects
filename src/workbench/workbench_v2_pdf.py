"""
Construction drawing PDF for workbench_v2.

Run with:
    uv run python src/workbench/workbench_v2_pdf.py

Outputs: src/workbench/workbench_v2_construction.pdf
"""

import math
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import cadquery as cq
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from workbench.workbench_v2 import (
    make_workbench, make_workbench_stage, get_bom, make_tabletop,
    TABLE_LENGTH, TABLE_WIDTH, LEG_HEIGHT, TABLE_THICKNESS,
    LEG_WIDTH, LEG_DEPTH, STRETCHER_WIDTH, APRON_THICKNESS, APRON_HEIGHT,
    STRETCHER_HEIGHT, STRETCHER_Z, EXT_DEPTH, EXT_LENGTH, FILLET_RADIUS, SLAT_WIDTH, SLAT_DEPTH,
    TENON_THICKNESS, TENON_HEIGHT, TENON_LENGTH, MORTISE_DEPTH,
)

OUTPUT_DIR = Path(__file__).parent
PAGE_W, PAGE_H = landscape(A3)
MARGIN = 15 * mm
TITLE_H = 18 * mm
DRAW_H = PAGE_H - MARGIN * 2 - TITLE_H
DRAW_W = PAGE_W - MARGIN * 2


# ── Helpers ───────────────────────────────────────────────────────────────────

def rotated(shape, axis, angle):
    return shape.rotate((0, 0, 0), axis, angle)


def iso_compound(compound):
    r = rotated(compound, (-1, 0, 0), 65)
    return rotated(r, (0, 1, 0), -35)


def export_temp_svg(compound, view_name, width=2400, height=1600, show_hidden=True):
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
            "showHidden": show_hidden,
        },
    )
    return Path(tmp.name)


def svg_to_rl(svg_path, target_w, target_h):
    drawing = svg2rlg(str(svg_path))
    if drawing is None:
        return None
    scale = min(target_w / drawing.width, target_h / drawing.height)
    drawing.width = drawing.width * scale
    drawing.height = drawing.height * scale
    drawing.transform = (scale, 0, 0, scale, 0, 0)
    return drawing


def parse_svg_transform(svg_path):
    """Return (sx, sy, tx, ty, svg_w, svg_h) from the first group transform in a CadQuery SVG."""
    try:
        tree = ET.parse(str(svg_path))
        root = tree.getroot()
        svg_w = float(root.get('width', 1800))
        svg_h = float(root.get('height', 1000))
        for elem in root.iter():
            t = elem.get('transform', '')
            if t:
                nums = re.findall(r'[-+]?\d+(?:\.\d+)?', t)
                if len(nums) >= 4:
                    sx, sy, tx, ty = (float(n) for n in nums[:4])
                    return sx, sy, tx, ty, svg_w, svg_h
    except Exception:
        pass
    return 1.0, -1.0, 0.0, 0.0, 1800.0, 1000.0


def make_coord_converter(svg_path, rl_drawing, canvas_ox, canvas_oy):
    """Return a callable (model_h, model_v) -> (canvas_x, canvas_y).

    model_h: horizontal model coordinate (mm) for this view
    model_v: vertical  model coordinate (mm) for this view (height = Z)
    """
    sx, sy, tx, ty, svg_w, svg_h = parse_svg_transform(svg_path)
    rl_scale = rl_drawing.width / svg_w   # mm per SVG pixel (isotropic)

    def convert(model_h: float, model_v: float):
        # Apply SVG group transform (scale + translate, applied R→L)
        svg_x = sx * (model_h + tx)
        svg_y = sy * (model_v + ty)        # sy is negative → y-flip built-in
        # RL has Y=0 at drawing bottom; SVG has Y=0 at top → flip
        rl_x = svg_x * rl_scale
        rl_y = (svg_h - svg_y) * rl_scale
        return canvas_ox + rl_x, canvas_oy + rl_y

    return convert


def place_drawing(c, rl_drawing, area_x, area_y, area_w, area_h, label=""):
    if rl_drawing is None:
        ox, oy, dw, dh = area_x, area_y, area_w, area_h
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
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.rect(area_x, area_y, area_w, area_h)
    if label:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.black)
        c.drawCentredString(area_x + area_w / 2, area_y + 3 * mm, label)
    return ox, oy, dw, dh


def draw_dimension_line(c, x1, y1, x2, y2, text, side="bottom", offset=8*mm, tick=3*mm):
    """Draw a dimension line with tick marks and centred label.
    side: 'bottom'/'top' for horizontal dims, 'left'/'right' for vertical dims.
    """
    c.setLineWidth(0.4)
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setFillColor(colors.HexColor("#333333"))

    if abs(x2 - x1) > abs(y2 - y1):  # horizontal
        sign = -1 if side == "bottom" else 1
        dy = sign * offset
        # dim line
        c.line(x1, y1 + dy, x2, y2 + dy)
        # ticks
        c.line(x1, y1, x1, y1 + dy + sign * tick)
        c.line(x2, y2, x2, y2 + dy + sign * tick)
        # arrows (small triangles)
        arrow = 2 * mm
        c.line(x1, y1 + dy, x1 + arrow, y1 + dy + arrow / 2)
        c.line(x1, y1 + dy, x1 + arrow, y1 + dy - arrow / 2)
        c.line(x2, y2 + dy, x2 - arrow, y2 + dy + arrow / 2)
        c.line(x2, y2 + dy, x2 - arrow, y2 + dy - arrow / 2)
        # label
        c.setFont("Helvetica", 7)
        c.drawCentredString((x1 + x2) / 2, y1 + dy + sign * (3 * mm), text)
    else:  # vertical
        sign = -1 if side == "left" else 1
        dx = sign * offset
        c.line(x1 + dx, y1, x2 + dx, y2)
        c.line(x1, y1, x1 + dx + sign * tick, y1)
        c.line(x2, y2, x2 + dx + sign * tick, y2)
        arrow = 2 * mm
        c.line(x1 + dx, y1, x1 + dx + arrow / 2, y1 + arrow)
        c.line(x1 + dx, y1, x1 + dx - arrow / 2, y1 + arrow)
        c.line(x2 + dx, y2, x2 + dx + arrow / 2, y2 - arrow)
        c.line(x2 + dx, y2, x2 + dx - arrow / 2, y2 - arrow)
        c.saveState()
        c.translate(x1 + dx - sign * (3 * mm), (y1 + y2) / 2)
        c.rotate(90)
        c.setFont("Helvetica", 7)
        c.drawCentredString(0, 0, text)
        c.restoreState()
    c.setFillColor(colors.black)


def draw_title_block(c, page_num, total_pages, title):
    bx, by, bw, bh = MARGIN, MARGIN, DRAW_W, TITLE_H
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(bx, by, bw, bh)
    c.line(bx + bw * 0.5, by, bx + bw * 0.5, by + bh)
    c.line(bx + bw * 0.75, by, bx + bw * 0.75, by + bh)
    c.line(bx + bw * 0.875, by, bx + bw * 0.875, by + bh)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(bx + 4, by + bh / 2 + 1, "Dennis Bakhuis — Workshop Workbench v2")
    c.setFont("Helvetica", 9)
    c.drawString(bx + bw * 0.5 + 4, by + bh / 2 + 1, title)
    c.drawString(bx + bw * 0.75 + 4, by + bh / 2 + 1, "Scale: NTS")
    c.drawString(bx + bw * 0.875 + 4, by + bh / 2 + 1, f"Sheet {page_num} of {total_pages}")


# ── Page builders ─────────────────────────────────────────────────────────────

def page_title(c, page_num, total_pages, iso_rl):
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN
    info_w = DRAW_W * 0.35
    tx = MARGIN + 6 * mm
    ty = content_y + content_h - 10 * mm
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#222222"))
    c.drawString(tx, ty, "WORKSHOP WORKBENCH")
    ty -= 10 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(tx, ty, "Version 2 — Construction Set")
    ty -= 12 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    specs = [
        ("Overall length", f"{TABLE_LENGTH} mm"),
        ("Overall depth", f"{TABLE_WIDTH + 200} mm (incl. extension)"),
        ("Height", f"{LEG_HEIGHT + TABLE_THICKNESS} mm"),
        ("Primary material", "Solid timber, European standard sizes"),
        ("Leg section", "75 × 75 mm"),
        ("Stretchers / Aprons", "50 × 75 mm"),
        ("Wall beam", "75 × 75 mm (wall-anchored)"),
        ("Slat panels", "20 × 15 mm, 10 mm gaps"),
        ("Twinset storage", "6× D12 twinsets (3 cols × 2 rows)"),
        ("Sheets included", f"{total_pages} (title, BOM, elevations, plan, manual, details)"),
    ]
    for label, val in specs:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(tx, ty, label + ":")
        c.setFont("Helvetica", 8)
        c.drawString(tx + 52 * mm, ty, val)
        ty -= 5.5 * mm
    iso_area_x = MARGIN + info_w + 6 * mm
    iso_area_w = DRAW_W - info_w - 6 * mm

    # Use colored PNG if available, otherwise fall back to SVG-based drawing
    colored_png = OUTPUT_DIR / "workbench_iso_colored.png"
    if colored_png.exists() and iso_rl is None:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(str(colored_png))
        iw, ih = img.getSize()
        scale = min(iso_area_w / iw, content_h / ih)
        dw, dh = iw * scale, ih * scale
        ox_ = iso_area_x + (iso_area_w - dw) / 2
        oy_ = content_y + (content_h - dh) / 2
        c.drawImage(str(colored_png), ox_, oy_, dw, dh)
    elif colored_png.exists():
        from reportlab.lib.utils import ImageReader
        img = ImageReader(str(colored_png))
        iw, ih = img.getSize()
        scale = min(iso_area_w / iw, content_h / ih)
        dw, dh = iw * scale, ih * scale
        ox_ = iso_area_x + (iso_area_w - dw) / 2
        oy_ = content_y + (content_h - dh) / 2
        c.drawImage(str(colored_png), ox_, oy_, dw, dh)
    else:
        place_drawing(c, iso_rl, iso_area_x, content_y, iso_area_w, content_h, "")
    draw_title_block(c, page_num, total_pages, "Title — Project Overview")
    c.showPage()


def page_bom(c, page_num, total_pages):
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN
    bom = get_bom()

    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(colors.HexColor("#222222"))
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "BILL OF MATERIALS")

    cols = [
        ("Part / Description", MARGIN + 2 * mm, 90 * mm),
        ("Material", MARGIN + 92 * mm, 52 * mm),
        ("Qty", MARGIN + 144 * mm, 12 * mm),
        ("W mm", MARGIN + 156 * mm, 14 * mm),
        ("D mm", MARGIN + 170 * mm, 14 * mm),
        ("L mm", MARGIN + 184 * mm, 14 * mm),
        ("Notes", MARGIN + 198 * mm, 60 * mm),
    ]

    row_h = 7 * mm
    header_y = content_y + content_h - 4 * mm

    c.setFillColor(colors.HexColor("#333333"))
    c.rect(MARGIN, header_y - row_h + 1.5 * mm, DRAW_W, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    for label, x, w in cols:
        c.drawString(x, header_y - row_h + 3.5 * mm, label)

    ty = header_y - row_h
    for i, item in enumerate(bom):
        bg = colors.HexColor("#f5f5f5") if i % 2 == 0 else colors.white
        c.setFillColor(bg)
        c.rect(MARGIN, ty - row_h + 1.5 * mm, DRAW_W, row_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold" if item.get("material") == "Steel" else "Helvetica", 8)

        def cell(text, x):
            c.drawString(x, ty - row_h + 3 * mm, str(text) if text is not None else "—")

        cell(item["part"], cols[0][1])
        c.setFont("Helvetica", 8)
        cell(item["material"], cols[1][1])
        cell(item["qty"], cols[2][1])
        cell(item.get("width_mm", ""), cols[3][1])
        cell(item.get("depth_mm", ""), cols[4][1])
        cell(item["length_mm"], cols[5][1])
        cell(item.get("note", ""), cols[6][1])
        ty -= row_h

    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.setLineWidth(0.3)
    for label, x, w in cols:
        c.line(x - 1 * mm, header_y - row_h * (len(bom) + 1) + 1.5 * mm, x - 1 * mm, header_y + 1.5 * mm)

    draw_title_block(c, page_num, total_pages, "Bill of Materials")
    c.showPage()


def page_elevations(c, page_num, total_pages, front_rl, side_rl, front_svg, side_svg):
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN
    half_w = DRAW_W / 2 - 2 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "ELEVATIONS")

    area_h = content_h - 10 * mm
    fx, fy, fw, fh = place_drawing(c, front_rl, MARGIN,             content_y + 10*mm, half_w, area_h, "FRONT ELEVATION")
    sx, sy, sw, sh = place_drawing(c, side_rl,  MARGIN+half_w+4*mm, content_y + 10*mm, half_w, area_h, "RIGHT SIDE ELEVATION")

    total_h = LEG_HEIGHT + TABLE_THICKNESS
    half_L  = TABLE_LENGTH / 2
    half_W  = TABLE_WIDTH  / 2

    # ── Front elevation: model horiz=X, model vert=Z ─────────────────────
    fc = make_coord_converter(front_svg, front_rl, fx, fy)
    fl_x,  f0_y    = fc(-half_L, 0)
    fr_x,  _       = fc(+half_L, 0)
    _,     ftop_y  = fc(0, total_h)
    _,     fleg_y  = fc(0, LEG_HEIGHT)
    _,     fstr_y  = fc(0, STRETCHER_Z)

    draw_dimension_line(c, fl_x, f0_y, fr_x, f0_y,
                        f"{TABLE_LENGTH} mm", side="bottom", offset=7*mm)
    draw_dimension_line(c, fr_x, f0_y, fr_x, ftop_y,
                        f"{total_h} mm", side="right", offset=9*mm)
    draw_dimension_line(c, fr_x, f0_y, fr_x, fleg_y,
                        f"{LEG_HEIGHT} mm", side="right", offset=20*mm)
    draw_dimension_line(c, fl_x, f0_y, fl_x, fstr_y,
                        f"{STRETCHER_Z} mm", side="left", offset=9*mm)

    # ── Side elevation: model horiz=Y (depth), model vert=Z ──────────────
    sc = make_coord_converter(side_svg, side_rl, sx, sy)
    sf_x, s0_y  = sc(-half_W, 0)
    sb_x, _     = sc(+half_W, 0)
    _,    stop_y = sc(0, total_h)

    draw_dimension_line(c, sf_x, s0_y, sb_x, s0_y,
                        f"{TABLE_WIDTH} mm", side="bottom", offset=7*mm)
    draw_dimension_line(c, sb_x, s0_y, sb_x, stop_y,
                        f"{total_h} mm", side="right", offset=9*mm)

    draw_title_block(c, page_num, total_pages, "Elevations — Front & Right Side")
    c.showPage()


def page_plan_iso(c, page_num, total_pages, top_rl, iso_rl, top_svg):
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN
    half_w = DRAW_W / 2 - 2 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "PLAN & 3D VIEW")

    area_h = content_h - 10 * mm
    px, py, pw, ph = place_drawing(c, top_rl, MARGIN,             content_y + 10*mm, half_w, area_h, "TOP PLAN")
    place_drawing(c, iso_rl, MARGIN + half_w + 4*mm, content_y + 10*mm, half_w, area_h, "ISOMETRIC VIEW")

    half_L = TABLE_LENGTH / 2
    half_W = TABLE_WIDTH  / 2

    # ── Top plan: model horiz=X, model vert=Y (depth) ────────────────────
    tc = make_coord_converter(top_svg, top_rl, px, py)
    tl_x, tf_y  = tc(-half_L, -half_W)   # left-front corner
    tr_x, _     = tc(+half_L, -half_W)   # right-front
    _,    tb_y  = tc(0, +half_W)          # back edge

    # Overall length (front edge, bottom)
    draw_dimension_line(c, tl_x, tf_y, tr_x, tf_y,
                        f"{TABLE_LENGTH} mm", side="bottom", offset=7*mm)
    # Main body depth (left side)
    draw_dimension_line(c, tl_x, tf_y, tl_x, tb_y,
                        f"{TABLE_WIDTH} mm", side="left", offset=9*mm)
    # Extension: right portion width (bottom, second row)
    ext_rx, _ = tc(+half_L, -half_W)
    ext_lx, _ = tc(+half_L - EXT_LENGTH, -half_W)
    draw_dimension_line(c, ext_lx, tf_y, ext_rx, tf_y,
                        f"{EXT_LENGTH} mm", side="bottom", offset=18*mm)
    # Extension depth (right side, bottom section)
    ext_back_y_val = -half_W + EXT_DEPTH     # top edge of extension in model Y
    _, ext_fb_y = tc(+half_L, -half_W + EXT_DEPTH)
    draw_dimension_line(c, ext_rx, tf_y, ext_rx, ext_fb_y,
                        f"{EXT_DEPTH} mm", side="right", offset=9*mm)

    draw_title_block(c, page_num, total_pages, "Plan & Isometric")
    c.showPage()


IKEA_STEPS = [
    {
        "stage": 0,
        "title": "Step 1 — Install All Legs",
        "icon": "1",
        "bullets": [
            "Cut all legs to 970 mm from 75×75 mm timber.",
            "Mark leg positions on the floor using the plan drawing.",
            "Three wall legs will be bolted directly to the wall — set aside.",
            "Stand all floor legs upright. Check plumb with a spirit level.",
        ],
        "parts": ["Leg 75×75 mm  ×  6 total"],
    },
    {
        "stage": 1,
        "title": "Step 2 — Fit Bottom Stretchers",
        "icon": "2",
        "bullets": [
            "Cut stretchers from 50×75 mm timber (see BOM for lengths).",
            "Cut mortises in legs: 18×60 mm, 32 mm deep, centred on face.",
            "Cut tenons on stretcher ends: 18×60×30 mm, 16 mm shoulders.",
            "Dry fit all joints before gluing.",
            "Position stretchers at 150 mm from floor (centre).",
            "Clamp in place and drill pocket-screw holes (Kreg jig or similar).",
            "Drive 2× 50 mm pocket screws per joint end. Do not overtighten.",
        ],
        "parts": ["Stretcher 50×75 mm  ×  2", "Pocket screw 50 mm  ×  8"],
    },
    {
        "stage": 2,
        "title": "Step 3 — Fit Top Aprons & Wall Beam",
        "icon": "3",
        "bullets": [
            "Cut aprons from 50×75 mm timber — same lengths as stretchers.",
            "Fix aprons at 933 mm from floor (centre), flush with leg inner faces.",
            "Mount wall beam (75×75 mm) to wall at apron height using M10×120 mm lag screws.",
            "Space lag screws at 600 mm centres — use rawlplugs in masonry.",
            "Bolt back apron to face of wall beam.",
        ],
        "parts": [
            "Apron 50×75 mm  ×  2",
            "Wall beam 75×75 mm  ×  1",
            "M10×120 lag screw  ×  6",
        ],
    },
    {
        "stage": 3,
        "title": "Step 4 — Lay the Tabletop",
        "icon": "4",
        "bullets": [
            "Cut tabletop to 2700 × 800 mm from 40 mm solid or engineered board.",
            "Lower onto frame. Check overhang is equal on all sides.",
            "Fix from below through apron top edge using pocket screws or figure-8 clips.",
            "Allow for wood movement — do not fully glue to frame.",
        ],
        "parts": ["Tabletop 2700×800×40 mm  ×  1", "Pocket screw 50 mm  ×  16"],
    },
    {
        "stage": 4,
        "title": "Step 5 — Fit Slat Mounting Rails",
        "icon": "5",
        "bullets": [
            "Cut front rails and right-side rail from 50×75 mm timber (see BOM).",
            "Position rails flush with leg inner faces — check alignment carefully.",
            "Slat wall sits 10 mm inside the leg outer face — rails go directly behind.",
            "Fix rails with 2× pocket screws per leg joint.",
        ],
        "parts": [
            "Slat mounting rail 50×75 mm  ×  3 (front ×2, right side ×1)",
            "Pocket screw 50 mm  ×  12",
        ],
    },
    {
        "stage": 5,
        "title": "Step 6 — Hang Slat Panels",
        "icon": "6",
        "bullets": [
            "Cut slats to height from 20×15 mm timber. Float 10 mm above floor.",
            "Space slats 10 mm apart — use a scrap spacer block for consistency.",
            "Drive 2× 3.5×35 mm screws per slat end (top and bottom rail).",
            "Front panel: slats run vertically across X, spaced along X.",
            "Left side panel: slats run vertically across Y, spaced along Y.",
        ],
        "parts": [
            "Slat 20×15 mm — see BOM for qty and length",
            "Wood screw 3.5×35 mm — see BOM for qty",
        ],
    },
]


def page_ikea_step(c, page_num, total_pages, step, stage_rl):
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN

    c.setFont("Helvetica-Bold", 60)
    c.setFillColor(colors.HexColor("#eeeeee"))
    c.drawString(MARGIN + 2 * mm, content_y + content_h - 18 * mm, step["icon"])

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#222222"))
    c.drawString(MARGIN + 26 * mm, content_y + content_h - 10 * mm, step["title"])

    c.setLineWidth(1.5)
    c.setStrokeColor(colors.HexColor("#333333"))
    c.line(MARGIN, content_y + content_h - 14 * mm, MARGIN + DRAW_W, content_y + content_h - 14 * mm)

    render_w = DRAW_W * 0.62
    render_h = content_h - 18 * mm
    place_drawing(c, stage_rl, MARGIN, content_y, render_w, render_h, "")

    tx = MARGIN + render_w + 8 * mm
    ty = content_y + content_h - 20 * mm
    col_w = DRAW_W - render_w - 10 * mm

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(tx, ty, "Instructions")
    ty -= 6 * mm
    c.setLineWidth(0.5)
    c.line(tx, ty + 2 * mm, tx + col_w, ty + 2 * mm)
    ty -= 2 * mm
    for bullet in step["bullets"]:
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.black)
        words = bullet.split()
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 8) < col_w - 6 * mm:
                line = test
            else:
                c.drawString(tx + 3 * mm, ty, "• " + line if not line.startswith("•") else line)
                ty -= 4.5 * mm
                line = word
        if line:
            c.drawString(tx + 3 * mm, ty, "• " + line)
            ty -= 4.5 * mm
        ty -= 1 * mm

    ty -= 4 * mm
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(tx, ty, "Parts used in this step")
    ty -= 6 * mm
    c.line(tx, ty + 2 * mm, tx + col_w, ty + 2 * mm)
    ty -= 2 * mm
    for part in step["parts"]:
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#333333"))
        c.drawString(tx + 3 * mm, ty, "\u2610  " + part)
        ty -= 5 * mm

    draw_title_block(c, page_num, total_pages, step["title"])
    c.showPage()


def page_details(c, page_num, total_pages):
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN

    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "DIMENSIONS & CONSTRUCTION DETAILS")

    dims = [
        ("Overall length", f"{TABLE_LENGTH} mm"),
        ("Overall width (main)", f"{TABLE_WIDTH} mm"),
        ("Extension depth", "200 mm"),
        ("Total depth", f"{TABLE_WIDTH + 200} mm"),
        ("Leg height", f"{LEG_HEIGHT} mm"),
        ("Tabletop thickness", f"{TABLE_THICKNESS} mm"),
        ("Overall height", f"{LEG_HEIGHT + TABLE_THICKNESS} mm"),
        ("Legs", "75 × 75 mm solid timber"),
        ("Stretchers", "50 × 75 mm (at 150 mm from floor)"),
        ("Aprons", "50 × 75 mm (at 933 mm from floor)"),
        ("Wall beam", "75 × 75 mm, wall-anchored"),
        ("Slats", "20 × 15 mm, 10 mm gaps"),
    ]

    tx = MARGIN + 4 * mm
    ty = content_y + content_h - 6 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(tx, ty, "KEY DIMENSIONS & MATERIALS")
    ty -= 6 * mm
    c.setLineWidth(0.3)
    c.line(tx, ty, tx + 120 * mm, ty)
    ty -= 5 * mm
    for label, value in dims:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(tx, ty, label + ":")
        c.setFont("Helvetica", 8)
        c.drawString(tx + 60 * mm, ty, value)
        ty -= 5 * mm

    tx2 = MARGIN + DRAW_W / 2 + 4 * mm
    ty2 = content_y + content_h - 6 * mm

    join_details = [
        ("1. LEG TO APRON & STRETCHER", [
            "2× pocket screws (50 mm) per joint.",
            "Apron flush with leg inner face.",
            "Pre-drill and countersink to avoid splitting.",
        ]),
        ("2. WALL BEAM TO WALL", [
            "75×75 mm beam at apron height (933 mm).",
            "M10×120 mm lag screws at 600 mm spacing.",
            "Use rawlplugs / expansion anchors for masonry.",
        ]),
        ("3. SLAT WALL MOUNTING", [
            "Two horizontal rails per slat wall (bottom + top).",
            "Slats fixed with 2× 3.5×35 mm screws per rail.",
            "10 mm gap between slats; 10 mm float above floor.",
        ]),
        ("4. TABLETOP", [
            "Screwed from below through apron top edge.",
            "Figure-8 clips or pocket screws for wood movement.",
        ]),
    ]

    c.setFont("Helvetica-Bold", 9)
    c.drawString(tx2, ty2, "CONSTRUCTION NOTES — JOINTS & FIXING")
    ty2 -= 6 * mm
    c.line(tx2, ty2, tx2 + 120 * mm, ty2)
    ty2 -= 5 * mm
    for title_text, lines in join_details:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(tx2, ty2, title_text)
        ty2 -= 5 * mm
        c.setFont("Helvetica", 7.5)
        for line in lines:
            c.drawString(tx2 + 3 * mm, ty2, line)
            ty2 -= 4.5 * mm
        ty2 -= 3 * mm

    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.line(MARGIN + DRAW_W / 2, content_y + 10 * mm, MARGIN + DRAW_W / 2, content_y + content_h)

    draw_title_block(c, page_num, total_pages, "Dimensions & Construction Details")
    c.showPage()


def page_tabletop_drawing(c, page_num, total_pages, iso_rl):
    """Full page: left = annotated 2D L-shape schematic, right = isometric CQ render."""
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN
    half_w = DRAW_W / 2 - 4 * mm

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "PART DRAWING — TABLETOP (L-SHAPED)")

    # ── Right panel: isometric render ─────────────────────────────────────
    place_drawing(c, iso_rl, MARGIN + half_w + 4 * mm, content_y + 10 * mm,
                  half_w, content_h - 10 * mm, "ISOMETRIC VIEW")

    # ── Left panel: 2D top-view schematic drawn with reportlab ────────────
    # Drawing area
    da_x = MARGIN + 4 * mm
    da_y = content_y + 10 * mm
    da_w = half_w - 8 * mm
    da_h = content_h - 20 * mm

    # Scale to fit: real dims 2700 × 1000mm
    real_L = TABLE_LENGTH        # 2700
    real_W = TABLE_WIDTH + EXT_DEPTH  # 1000
    sx = (da_w - 40 * mm) / real_L   # leave margin for dim lines
    sy = (da_h - 40 * mm) / real_W
    scale = min(sx, sy)

    # Origin = top-left of schematic, centred in panel
    draw_w = real_L * scale
    draw_h = real_W * scale
    ox = da_x + (da_w - draw_w) / 2 + 8 * mm
    oy = da_y + (da_h - draw_h) / 2 + 8 * mm

    # EXT_LENGTH scaled
    ext_l = EXT_LENGTH * scale
    main_d = TABLE_WIDTH * scale
    ext_d = EXT_DEPTH * scale
    fillet_r = 100 * scale

    # ── L-shape vertices ──────────────────────────────────────────────────
    # Correct 6-point L boundary: main body (800mm) TOP, extension BOTTOM-RIGHT.
    #
    #  A ────────────────────────── B
    #  |   MAIN BODY (800mm)       |
    #  |   2700mm wide             |
    #  G ──────────── D ~~~~~~~~~~~|  ← 800mm from top; fillet at D
    #                 |  EXTENSION |
    #                 E ───────────C_ext
    #
    #   A = top-left        (ox,              oy+draw_h)
    #   B = top-right       (ox+draw_w,       oy+draw_h)
    #   C_ext = ext b-right (ox+draw_w,       oy)            ← right edge goes full depth
    #   E = ext b-left/step (ox+draw_w-ext_l, oy)            ← sharp corner
    #   D = inside corner   (ox+draw_w-ext_l, oy+ext_d)      ← FILLET HERE
    #   G = main body b-l   (ox,              oy+ext_d)

    A     = (ox,                  oy + draw_h)
    B     = (ox + draw_w,         oy + draw_h)
    C_ext = (ox + draw_w,         oy)               # ext bottom-right
    E_    = (ox + draw_w - ext_l, oy)               # ext bottom-left (sharp corner)
    D     = (ox + draw_w - ext_l, oy + ext_d)       # inside corner → fillet
    G     = (ox,                  oy + ext_d)        # main body bottom-left

    # Fillet at D: path arrives going UP (E→D), departs going LEFT (D→G).
    # Arc centre inside shape = (D[0]-fillet_r, D[1]-fillet_r)
    # Start tangent (East, on E→D going UP): (D[0],          D[1]-fillet_r)  → 0°
    # End   tangent (North, on D→G going LEFT): (D[0]-fillet_r, D[1])        → 90°
    # Sweep: CCW from 0° (East) +90° → 90° (North)
    arc_cx = D[0] - fillet_r
    arc_cy = D[1] - fillet_r   # = oy + ext_d - fillet_r

    c.setStrokeColor(colors.HexColor("#222222"))
    c.setFillColor(colors.HexColor("#f0e8d8"))
    c.setLineWidth(1.2)

    p = c.beginPath()
    p.moveTo(*A)
    p.lineTo(*B)
    p.lineTo(*C_ext)                              # right edge: full depth to bottom
    p.lineTo(*E_)                                 # extension bottom: left to step
    p.lineTo(D[0], D[1] - fillet_r)              # step: up to arc start (East tangent)
    p.arcTo(arc_cx - fillet_r, arc_cy - fillet_r,
            arc_cx + fillet_r, arc_cy + fillet_r,
            0, 90)                               # CCW East(0°) → North(90°)
    # now at North tangent: (D[0]-fillet_r, D[1]) = (arc_cx, oy+ext_d)
    p.lineTo(*G)                                  # main body bottom, going left
    p.lineTo(*A)                                  # left edge, going up
    p.close()
    c.drawPath(p, fill=1, stroke=1)

    # ── Extension boundary line (same style as plank lines) ──────────────
    # Drawn AFTER fill so it's always on top.
    plank_color = colors.HexColor("#8B6914")
    c.setStrokeColor(plank_color)
    c.setLineWidth(0.7)
    c.setDash(4, 3)
    c.line(G[0], G[1], ox + draw_w, G[1])
    c.setDash()

    # ── Dimension lines ───────────────────────────────────────────────────
    # Overall length (top)
    draw_dimension_line(c, A[0], A[1], B[0], B[1],
                        f"{TABLE_LENGTH} mm", side="top", offset=7*mm)
    # Left depth: G→A = 800mm (main body only)
    draw_dimension_line(c, G[0], G[1], A[0], A[1],
                        f"{TABLE_WIDTH} mm", side="left", offset=9*mm)
    # Right depth upper: B down to C_ext level at oy+ext_d = 800mm
    C_step = (ox + draw_w, oy + ext_d)
    draw_dimension_line(c, B[0], B[1], C_step[0], C_step[1],
                        f"{TABLE_WIDTH} mm", side="right", offset=9*mm)
    # Right depth lower: ext_d = 200mm
    draw_dimension_line(c, C_step[0], C_step[1], C_ext[0], C_ext[1],
                        f"{EXT_DEPTH} mm", side="right", offset=9*mm)
    # Extension width (bottom, E→C_ext)
    draw_dimension_line(c, E_[0], E_[1], C_ext[0], E_[1],
                        f"{EXT_LENGTH} mm", side="bottom", offset=7*mm)

    # Fillet label — just below D, in the notch area
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(D[0] + 2 * mm, D[1] - fillet_r - 4 * mm, f"R {FILLET_RADIUS} mm")

    # ── Plank division lines ──────────────────────────────────────────────
    # Main body: 4 planks × 200mm, measured from TOP of main body downward.
    # Bottom of main body = oy + ext_d.  Top = oy + draw_h = oy + ext_d + main_d.
    # Plank seams at ext_d + 200, ext_d + 400, ext_d + 600mm from bottom.
    PLANK_W_MM = 200
    N_PLANKS   = TABLE_WIDTH // PLANK_W_MM   # = 4
    plank_color = colors.HexColor("#8B6914")

    c.setStrokeColor(plank_color)
    c.setLineWidth(0.7)
    c.setDash(4, 3)

    for i in range(1, N_PLANKS):
        # Lines go from bottom of main body (G[1]=oy+ext_d) upward in 200mm steps
        py = G[1] + i * PLANK_W_MM * scale
        c.line(ox, py, ox + draw_w, py)   # full width (all within main body ✓)

    c.setDash()
    c.setLineWidth(0.5)

    # Plank labels: centred in each plank band, on left edge
    c.setFont("Helvetica", 6.5)
    c.setFillColor(plank_color)
    for i in range(N_PLANKS):
        # Band i goes from G[1] + i*200*scale to G[1] + (i+1)*200*scale
        label_y = G[1] + i * PLANK_W_MM * scale + (PLANK_W_MM * scale / 2)
        c.drawString(ox + 2 * mm, label_y - 2 * mm, f"{PLANK_W_MM} mm")

    # Extension label (centred in extension rectangle)
    c.setFont("Helvetica", 6.5)
    c.setFillColor(colors.HexColor("#444444"))
    ext_cx = E_[0] + ext_l / 2   # centre X of extension = D[0] + ext_l/2
    ext_cy = oy + ext_d / 2      # centre Y of extension
    c.drawCentredString(ext_cx, ext_cy + 2 * mm, "uitbouw")
    c.drawCentredString(ext_cx, ext_cy - 2 * mm, f"{EXT_LENGTH:.0f}×{EXT_DEPTH} mm")

    # Material callout (centre-left of main body, well away from extension)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#222222"))
    note_x = ox + (draw_w - ext_l) / 2
    note_y = G[1] + main_d / 2
    c.drawCentredString(note_x, note_y + 4 * mm, f"Dikte: {TABLE_THICKNESS} mm")
    c.drawCentredString(note_x, note_y,           "Beuken gestoomd 52 mm")
    c.drawCentredString(note_x, note_y - 4 * mm, "Edge-glued · 4 planken")
    c.drawCentredString(note_x, note_y - 8 * mm, f"{N_PLANKS} × {PLANK_W_MM} × 2700 mm")

    # Panel border
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.setLineWidth(0.3)
    c.rect(da_x, da_y, da_w, da_h)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawCentredString(da_x + da_w / 2, da_y + 3 * mm, "TOP VIEW (schematic, NTS)")

    draw_title_block(c, page_num, total_pages, "Part Drawing — Tabletop")
    c.showPage()


def _draw_iso_box(c, ox, oy, w, d, h, scale, label, dims_text):
    """Draw a simple isometric-projection box with reportlab, annotated."""
    # isometric offsets per unit
    ix, iy = 0.5 * scale, 0.25 * scale   # x-axis dir
    jx, jy = -0.5 * scale, 0.25 * scale  # y-axis dir
    kx, ky = 0, scale                     # z-axis (up)

    def pt(xi, yi, zi):
        return (ox + xi * ix + yi * jx, oy + xi * iy + yi * jy + zi * ky)

    # 8 corners
    p000 = pt(0, 0, 0);   p100 = pt(w, 0, 0)
    p010 = pt(0, d, 0);   p110 = pt(w, d, 0)
    p001 = pt(0, 0, h);   p101 = pt(w, 0, h)
    p011 = pt(0, d, h);   p111 = pt(w, d, h)

    c.setFillColor(colors.HexColor("#c8a96e"))
    c.setStrokeColor(colors.HexColor("#5a3a1a"))
    c.setLineWidth(0.6)

    # Top face
    tp = c.beginPath()
    tp.moveTo(*p001); tp.lineTo(*p101); tp.lineTo(*p111); tp.lineTo(*p011); tp.close()
    c.drawPath(tp, fill=1, stroke=1)

    # Front face (y=0 plane)
    fp = c.beginPath()
    fp.moveTo(*p000); fp.lineTo(*p100); fp.lineTo(*p101); fp.lineTo(*p001); fp.close()
    c.setFillColor(colors.HexColor("#b08040"))
    c.drawPath(fp, fill=1, stroke=1)

    # Right face (x=w plane)
    rp = c.beginPath()
    rp.moveTo(*p100); rp.lineTo(*p110); rp.lineTo(*p111); rp.lineTo(*p101); rp.close()
    c.setFillColor(colors.HexColor("#9a6e30"))
    c.drawPath(rp, fill=1, stroke=1)

    # Part label above
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(ox, oy + h * ky + 6 * mm, label)

    # Dimension annotations
    c.setFont("Helvetica", 6.5)
    for i, txt in enumerate(dims_text):
        c.drawCentredString(ox, oy - 5 * mm - i * 4 * mm, txt)


def page_timber_parts(c, page_num, total_pages):
    """One page: annotated isometric drawings of all unique timber sections."""
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "TIMBER PARTS — INDIVIDUAL PART DRAWINGS")

    bom = get_bom()
    timber_bom = [b for b in bom if b["material"] not in ("Steel", "Steel (hot-dip galv.)") and b["part"] != "Tabletop panel"]

    # Layout: 3 columns × 2 rows
    n_cols = 3
    cell_w = DRAW_W / n_cols
    cell_h = (content_h - 10 * mm) / 2

    iso_scale = 0.045  # mm → points at a sensible visual size, tweak if needed

    for idx, item in enumerate(timber_bom[:6]):  # up to 6 parts in 3×2 grid
        col = idx % n_cols
        row = idx // n_cols
        cx = MARGIN + col * cell_w + cell_w / 2
        cy = content_y + content_h - 10 * mm - row * cell_h - cell_h * 0.35

        w = item.get("width_mm") or 50
        d = item.get("depth_mm") or 75
        l = item.get("length_mm") or 900

        # Clamp visual length so it doesn't overflow
        vis_l = min(l, 500)

        _draw_iso_box(
            c, cx, cy,
            w=w * iso_scale,
            d=d * iso_scale,
            h=vis_l * iso_scale,
            scale=1.0,
            label=item["part"].split("—")[0].strip(),
            dims_text=[
                f"Section: {w} × {d} mm",
                f"Length: {l} mm",
                f"Qty: {item['qty']}",
                item.get("note", ""),
            ],
        )

        # Cell border
        c.setLineWidth(0.2)
        c.setStrokeColor(colors.HexColor("#dddddd"))
        c.rect(MARGIN + col * cell_w, content_y + content_h - 10 * mm - (row + 1) * cell_h,
               cell_w, cell_h)

    draw_title_block(c, page_num, total_pages, "Timber Parts — Individual Drawings")
    c.showPage()


def page_joinery_detail(c, page_num, total_pages):
    """Detail page: Mortise & Tenon joint drawings (pen & gat)."""
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN
    half_w = DRAW_W / 2 - 4 * mm

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "VERBINDINGSDETAIL — PEN & GAT (M&T)")

    SCALE = 1.7 * mm  # paper-pt per real-mm (gives ~85mm on paper for 50mm real)

    # ── Derived drawing sizes (in points) ───────────────────────────────────
    sw   = STRETCHER_WIDTH  * SCALE          # stretcher width (50mm → ~85mm paper)
    sh   = STRETCHER_HEIGHT * SCALE          # stretcher height (75mm → ~127.5mm paper)
    tt   = TENON_THICKNESS  * SCALE          # tenon thickness (18mm → ~30.6mm paper)
    th   = TENON_HEIGHT     * SCALE          # tenon height (60mm → ~102mm paper)
    tl   = TENON_LENGTH     * SCALE          # tenon length (30mm → ~51mm paper)
    shl_w = (STRETCHER_WIDTH  - TENON_THICKNESS) / 2 * SCALE   # shoulder w = 16mm
    shl_h = (STRETCHER_HEIGHT - TENON_HEIGHT)    / 2 * SCALE   # shoulder h = 7.5mm
    lw   = LEG_WIDTH  * SCALE                # leg face width (75mm → ~127.5mm paper)
    lh   = LEG_DEPTH  * SCALE                # leg face depth (75mm → ~127.5mm paper)
    mw   = TENON_THICKNESS * SCALE           # mortise width = tenon thickness
    mh   = TENON_HEIGHT    * SCALE           # mortise height = tenon height

    # ── Notes at bottom of content area ─────────────────────────────────────
    notes_h = 22 * mm
    notes_y = content_y + 2 * mm
    notes = [
        "Verlijmen met D3 houtlijm. Pen volledig insmeren, gat droog laten.",
        "Klemmen: 30 min. Uithardingstijd: 24h voor belasting.",
        "Freesmachine met rechte frees of gatenboor + beitel.",
    ]
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#333333"))
    for i, note in enumerate(notes):
        c.drawString(MARGIN + 4 * mm, notes_y + (len(notes) - 1 - i) * 6 * mm, "\u2022 " + note)

    # ── Panel layout ─────────────────────────────────────────────────────────
    lp_x = MARGIN + 4 * mm
    lp_y = content_y + notes_h + 2 * mm
    lp_w = half_w - 8 * mm
    lp_h = content_h - notes_h - 6 * mm

    rp_x = MARGIN + half_w + 4 * mm
    rp_y = lp_y
    rp_w = lp_w
    rp_h = lp_h

    # ── Left panel: Tenon (side view of stretcher end, Y-Z plane) ────────────
    # Center the total drawing (stretcher body + tenon extension) in the panel
    draw_total_w = sw + tl
    draw_total_h = sh
    sx = lp_x + (lp_w - draw_total_w) / 2
    sy = lp_y + 12 * mm + (lp_h - 12 * mm - draw_total_h) / 2  # 12mm for bottom label

    # Stretcher cross-section body
    c.setFillColor(colors.HexColor("#d4b896"))
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(1.2)
    c.rect(sx, sy, sw, sh, fill=1, stroke=1)

    # Tenon interior (darker, within the cross-section)
    tenon_x = sx + shl_w
    tenon_y = sy + shl_h
    c.setFillColor(colors.HexColor("#b8925a"))
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(0.8)
    c.rect(tenon_x, tenon_y, tt, th, fill=1, stroke=1)

    # Tenon extension (part that projects into the mortise)
    c.setFillColor(colors.HexColor("#c8a070"))
    c.setStrokeColor(colors.HexColor("#555555"))
    c.setLineWidth(0.8)
    c.rect(sx + sw, tenon_y, tl, th, fill=1, stroke=1)

    # Shoulder lines (dashed)
    c.setStrokeColor(colors.HexColor("#666666"))
    c.setLineWidth(0.5)
    c.setDash(4, 3)
    c.line(sx, tenon_y,        sx + sw, tenon_y)           # bottom shoulder (horiz)
    c.line(sx, tenon_y + th,   sx + sw, tenon_y + th)      # top shoulder (horiz)
    c.line(tenon_x,      sy,   tenon_x,      sy + sh)      # left shoulder (vert)
    c.line(tenon_x + tt, sy,   tenon_x + tt, sy + sh)      # right shoulder (vert)
    c.setDash()

    # Dimension lines — tenon panel
    draw_dimension_line(c, sx, sy, sx + sw, sy,
                        f"{STRETCHER_WIDTH} mm", side="bottom", offset=8 * mm)
    draw_dimension_line(c, sx, sy, tenon_x, sy,
                        f"{int((STRETCHER_WIDTH - TENON_THICKNESS) // 2)} mm",
                        side="bottom", offset=16 * mm)
    draw_dimension_line(c, tenon_x, sy + sh, tenon_x + tt, sy + sh,
                        f"{TENON_THICKNESS} mm", side="top", offset=6 * mm)
    draw_dimension_line(c, sx, sy, sx, sy + sh,
                        f"{STRETCHER_HEIGHT} mm", side="left", offset=10 * mm)
    draw_dimension_line(c, sx + sw + tl, tenon_y, sx + sw + tl, tenon_y + th,
                        f"{TENON_HEIGHT} mm", side="right", offset=8 * mm)
    draw_dimension_line(c, sx + sw, tenon_y + th, sx + sw + tl, tenon_y + th,
                        f"{TENON_LENGTH} mm", side="top", offset=6 * mm)

    # Panel border and label
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.rect(lp_x, lp_y, lp_w, lp_h)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawCentredString(lp_x + lp_w / 2, lp_y + 3 * mm, "PEN (zijaanzicht eindvlak, Y-Z vlak)")

    # ── Right panel: Mortise (front view of leg face, X-Z plane) ─────────────
    leg_x = rp_x + (rp_w - lw) / 2
    leg_y = rp_y + (rp_h - lh) / 2 + 5 * mm  # slightly above centre for bottom dims

    # Leg face
    c.setFillColor(colors.HexColor("#d4b896"))
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(1.2)
    c.rect(leg_x, leg_y, lw, lh, fill=1, stroke=1)

    # Mortise (centred on leg face)
    m_x = leg_x + (lw - mw) / 2
    m_y = leg_y + (lh - mh) / 2

    c.setFillColor(colors.HexColor("#4a2a0a"))   # very dark = hole
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(0.8)
    c.rect(m_x, m_y, mw, mh, fill=1, stroke=1)

    # Centre lines (dashed)
    c.setStrokeColor(colors.HexColor("#888888"))
    c.setLineWidth(0.4)
    c.setDash(3, 3)
    c.line(leg_x, leg_y + lh / 2, leg_x + lw, leg_y + lh / 2)   # horizontal CL
    c.line(leg_x + lw / 2, leg_y, leg_x + lw / 2, leg_y + lh)   # vertical CL
    c.setDash()

    # Dimension lines — mortise panel
    draw_dimension_line(c, leg_x, leg_y, leg_x + lw, leg_y,
                        f"{LEG_WIDTH} mm", side="bottom", offset=8 * mm)
    draw_dimension_line(c, leg_x, leg_y, leg_x, leg_y + lh,
                        f"{LEG_DEPTH} mm", side="left", offset=8 * mm)
    draw_dimension_line(c, m_x, leg_y, m_x + mw, leg_y,
                        f"{TENON_THICKNESS} mm", side="bottom", offset=16 * mm)
    draw_dimension_line(c, leg_x + lw, m_y, leg_x + lw, m_y + mh,
                        f"{TENON_HEIGHT} mm", side="right", offset=8 * mm)

    # Mortise depth callout (inside leg face, right of mortise)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#222222"))
    depth_note_x = m_x + mw + 4 * mm
    depth_note_y = m_y + mh / 2 - 2 * mm
    c.drawString(depth_note_x, depth_note_y, f"Diepte: {MORTISE_DEPTH} mm")
    c.setLineWidth(0.4)
    c.setStrokeColor(colors.HexColor("#555555"))
    c.line(m_x + mw, m_y + mh / 2, depth_note_x - 1 * mm, depth_note_y + 2 * mm)

    # Panel border and label
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.rect(rp_x, rp_y, rp_w, rp_h)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawCentredString(rp_x + rp_w / 2, rp_y + 3 * mm, "GAT (vooraanzicht pootvlak, X-Z vlak)")

    draw_title_block(c, page_num, total_pages, "Verbindingsdetail — Pen & Gat (M&T)")
    c.showPage()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Building workbench model...")
    workbench = make_workbench(include_props=False)
    compound = workbench.toCompound()

    # Separate model with props for the title page iso view
    workbench_props = make_workbench(include_props=True)
    compound_props = workbench_props.toCompound()

    front_comp = rotated(compound, (-1, 0, 0), 90)
    side_comp = rotated(front_comp, (0, -1, 0), 90)
    iso_comp = iso_compound(compound)
    iso_comp_props = iso_compound(compound_props)

    print("Exporting orthographic SVGs...")
    top_svg = export_temp_svg(compound, "top", 1800, 1000)
    front_svg = export_temp_svg(front_comp, "front", 1800, 1000)
    side_svg = export_temp_svg(side_comp, "side", 1000, 1000)
    iso_svg = export_temp_svg(iso_comp, "iso", 1800, 1000)
    iso_props_svg = export_temp_svg(iso_comp_props, "iso_props", 1800, 1000)

    print("Exporting assembly stage SVGs...")
    stage_svgs = []
    for step in IKEA_STEPS:
        print(f"  Stage {step['stage']}: {step['title']}")
        stage_assy = make_workbench_stage(step["stage"])
        stage_compound = stage_assy.toCompound()
        stage_iso = iso_compound(stage_compound)
        svg = export_temp_svg(stage_iso, f"stage_{step['stage']}", 2000, 1200, show_hidden=False)
        stage_svgs.append(svg)

    print("Generating individual part SVGs...")
    part_svgs = {}

    # Tabletop — render the actual L-shape (iso only; top view drawn directly with reportlab)
    tabletop_shape = make_tabletop()
    tabletop_iso_shape = iso_compound(tabletop_shape.val())
    part_svgs["tabletop_iso"] = export_temp_svg(tabletop_iso_shape, "part_tabletop_iso", 2400, 1400, show_hidden=False)

    # Generic timber parts — render a box for each unique dimension
    def make_box_part(w, d, l):
        return cq.Workplane("XY").box(w, d, l).val()

    # Render each timber type
    timber_parts = [
        ("leg", LEG_WIDTH, LEG_DEPTH, LEG_HEIGHT),
        ("stretcher_apron", STRETCHER_WIDTH, 75, 900),  # representative length
        ("slat", SLAT_WIDTH, SLAT_DEPTH, 940),
    ]
    for name, w, d, l in timber_parts:
        part = make_box_part(w, d, l)
        iso = iso_compound(part)
        part_svgs[f"timber_{name}"] = export_temp_svg(iso, f"part_{name}", 800, 600, show_hidden=False)

    total_pages = 1 + 1 + 1 + 1 + len(IKEA_STEPS) + 1 + 3  # title + BOM + elev + plan + ikea*6 + details + tabletop + joinery + timber

    half_w = DRAW_W / 2 - 2 * mm
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN

    print("Converting SVGs to reportlab drawings...")
    iso_rl = svg_to_rl(iso_props_svg, DRAW_W * 0.6, content_h)   # title page: with props
    front_rl = svg_to_rl(front_svg, half_w - 4 * mm, content_h - 14 * mm)
    side_rl = svg_to_rl(side_svg, half_w - 4 * mm, content_h - 14 * mm)
    top_rl = svg_to_rl(top_svg, half_w - 4 * mm, content_h - 14 * mm)

    out_path = OUTPUT_DIR / "workbench_v2_construction.pdf"
    c = canvas.Canvas(str(out_path), pagesize=landscape(A3))

    pn = 1
    page_title(c, pn, total_pages, iso_rl); pn += 1
    page_bom(c, pn, total_pages); pn += 1
    page_elevations(c, pn, total_pages, front_rl, side_rl, front_svg, side_svg); pn += 1
    page_plan_iso(c, pn, total_pages, top_rl, iso_rl, top_svg); pn += 1

    for i, step in enumerate(IKEA_STEPS):
        stage_rl = svg_to_rl(stage_svgs[i], DRAW_W * 0.62 - 4 * mm, content_h - 20 * mm)
        page_ikea_step(c, pn, total_pages, step, stage_rl); pn += 1

    page_details(c, pn, total_pages); pn += 1

    # Part drawings
    tabletop_iso_rl = svg_to_rl(part_svgs["tabletop_iso"], half_w - 4 * mm, content_h - 20 * mm)
    page_tabletop_drawing(c, pn, total_pages, tabletop_iso_rl); pn += 1
    page_joinery_detail(c, pn, total_pages); pn += 1
    page_timber_parts(c, pn, total_pages); pn += 1

    c.save()
    print(f"PDF saved: {out_path}")

    for p in [top_svg, front_svg, side_svg, iso_svg] + stage_svgs:
        p.unlink(missing_ok=True)

    for p in part_svgs.values():
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
