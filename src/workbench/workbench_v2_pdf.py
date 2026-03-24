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
from workbench.workbench_v2 import (
    make_workbench, make_workbench_stage, get_bom,
    TABLE_LENGTH, TABLE_WIDTH, LEG_HEIGHT, TABLE_THICKNESS,
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


def export_temp_svg(compound, view_name, width=1800, height=1000, show_hidden=True):
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


def place_drawing(c, rl_drawing, area_x, area_y, area_w, area_h, label=""):
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
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.rect(area_x, area_y, area_w, area_h)
    if label:
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.black)
        c.drawCentredString(area_x + area_w / 2, area_y + 3 * mm, label)


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


def page_elevations(c, page_num, total_pages, front_rl, side_rl):
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN
    half_w = DRAW_W / 2 - 2 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "ELEVATIONS")
    place_drawing(c, front_rl, MARGIN, content_y + 10 * mm, half_w, content_h - 10 * mm, "FRONT ELEVATION")
    place_drawing(c, side_rl, MARGIN + half_w + 4 * mm, content_y + 10 * mm, half_w, content_h - 10 * mm, "RIGHT SIDE ELEVATION")
    draw_title_block(c, page_num, total_pages, "Elevations — Front & Right Side")
    c.showPage()


def page_plan_iso(c, page_num, total_pages, top_rl, iso_rl):
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN
    half_w = DRAW_W / 2 - 2 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, content_y + content_h + 2 * mm, "PLAN & 3D VIEW")
    place_drawing(c, top_rl, MARGIN, content_y + 10 * mm, half_w, content_h - 10 * mm, "TOP PLAN")
    place_drawing(c, iso_rl, MARGIN + half_w + 4 * mm, content_y + 10 * mm, half_w, content_h - 10 * mm, "ISOMETRIC VIEW")
    draw_title_block(c, page_num, total_pages, "Plan & Isometric")
    c.showPage()


IKEA_STEPS = [
    {
        "stage": 0,
        "title": "Step 1 — Install All Legs",
        "icon": "1",
        "bullets": [
            "Cut all legs to 960 mm from 75×75 mm timber.",
            "Mark leg positions on the floor using the plan drawing.",
            "Three wall legs will be bolted directly to the wall — set aside.",
            "Stand all floor legs upright. Check plumb with a spirit level.",
        ],
        "parts": ["Leg 75×75 mm  ×  8 total"],
    },
    {
        "stage": 1,
        "title": "Step 2 — Fit Bottom Stretchers",
        "icon": "2",
        "bullets": [
            "Cut stretchers from 50×75 mm timber (see BOM for lengths).",
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
            "Fix aprons at 885 mm from floor (centre), flush with leg inner faces.",
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
            "Slat wall sits 15 mm inside the leg outer face — rails go directly behind.",
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
        ("Aprons", "50 × 75 mm (at 885 mm from floor)"),
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
            "75×75 mm beam at apron height (885 mm).",
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Building workbench model...")
    workbench = make_workbench(include_props=False)
    compound = workbench.toCompound()

    front_comp = rotated(compound, (-1, 0, 0), 90)
    side_comp = rotated(front_comp, (0, -1, 0), 90)
    iso_comp = iso_compound(compound)

    print("Exporting orthographic SVGs...")
    top_svg = export_temp_svg(compound, "top", 1800, 1000)
    front_svg = export_temp_svg(front_comp, "front", 1800, 1000)
    side_svg = export_temp_svg(side_comp, "side", 1000, 1000)
    iso_svg = export_temp_svg(iso_comp, "iso", 1800, 1000)

    print("Exporting assembly stage SVGs...")
    stage_svgs = []
    for step in IKEA_STEPS:
        print(f"  Stage {step['stage']}: {step['title']}")
        stage_assy = make_workbench_stage(step["stage"])
        stage_compound = stage_assy.toCompound()
        stage_iso = iso_compound(stage_compound)
        svg = export_temp_svg(stage_iso, f"stage_{step['stage']}", 1600, 900, show_hidden=False)
        stage_svgs.append(svg)

    total_pages = 1 + 1 + 1 + 1 + len(IKEA_STEPS) + 1  # title + BOM + elev + plan + ikea*6 + details

    half_w = DRAW_W / 2 - 2 * mm
    content_y = MARGIN + TITLE_H + 4 * mm
    content_h = PAGE_H - content_y - MARGIN

    print("Converting SVGs to reportlab drawings...")
    iso_rl = svg_to_rl(iso_svg, DRAW_W * 0.6, content_h)
    front_rl = svg_to_rl(front_svg, half_w - 4 * mm, content_h - 14 * mm)
    side_rl = svg_to_rl(side_svg, half_w - 4 * mm, content_h - 14 * mm)
    top_rl = svg_to_rl(top_svg, half_w - 4 * mm, content_h - 14 * mm)

    out_path = OUTPUT_DIR / "workbench_v2_construction.pdf"
    c = canvas.Canvas(str(out_path), pagesize=landscape(A3))

    pn = 1
    page_title(c, pn, total_pages, iso_rl); pn += 1
    page_bom(c, pn, total_pages); pn += 1
    page_elevations(c, pn, total_pages, front_rl, side_rl); pn += 1
    page_plan_iso(c, pn, total_pages, top_rl, iso_rl); pn += 1

    for i, step in enumerate(IKEA_STEPS):
        stage_rl = svg_to_rl(stage_svgs[i], DRAW_W * 0.62 - 4 * mm, content_h - 20 * mm)
        page_ikea_step(c, pn, total_pages, step, stage_rl); pn += 1

    page_details(c, pn, total_pages); pn += 1

    c.save()
    print(f"PDF saved: {out_path}")

    for p in [top_svg, front_svg, side_svg, iso_svg] + stage_svgs:
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
