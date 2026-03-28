"""
HBM Verrijdbare Gereedschapswagen met Houten Werkblad — 146 cm (zwart)
CadQuery prop / helper object for workspace layout planning.

Product: https://www.hbm-machines.com/nl/p/hbm-verrijdbare-gereedschapswagen-met-houten-werkblad-146-cm-zwart

Confirmed dimensions:
  Width:          1460 mm  (from product name "146 cm")
  Top thickness:   40 mm  (product spec)

Estimated dimensions (from image proportional analysis):
  Depth:           520 mm
  Total height:    950 mm  (floor to top of wood surface, incl. wheels)
  Wheel height:    125 mm  (5" swivel casters)
  Top overhang:     25 mm  (all sides)

⚠️  Verify exact depth and height with physical unit before finalising layout.
    Clearance under workbench (LEG_HEIGHT=970mm) is ~20mm — very tight.
"""

import cadquery as cq
from cadquery import Assembly, Color, Location, Vector

# ── Parameters ───────────────────────────────────────────────────────────────

CART_WIDTH          = 1460   # mm, X direction (confirmed)
CART_DEPTH          = 520    # mm, Y direction (estimated)
CART_TOTAL_HEIGHT   = 950    # mm, Z direction, floor to top of wood (estimated)
CART_TOP_THICKNESS  = 40     # mm (confirmed)
CART_WHEEL_HEIGHT   = 125    # mm, floor clearance on casters (estimated)
CART_TOP_OVERHANG   = 25     # mm, overhang of wood top on each side (estimated)

# Derived
CART_BODY_HEIGHT = CART_TOTAL_HEIGHT - CART_TOP_THICKNESS - CART_WHEEL_HEIGHT
CART_BODY_WIDTH  = CART_WIDTH  - 2 * CART_TOP_OVERHANG
CART_BODY_DEPTH  = CART_DEPTH  - 2 * CART_TOP_OVERHANG

# Number of drawers per column and columns
DRAWER_COLS   = 3
DRAWER_ROWS   = 7   # approximate visible rows in main columns
DRAWER_H_SMALL = CART_BODY_HEIGHT / 10     # small drawers
DRAWER_H_LARGE = CART_BODY_HEIGHT / 5      # large bottom drawer
DRAWER_INSET  = 3   # how much drawer face is recessed from body face

# Handle
HANDLE_R      = 12    # tube radius mm
HANDLE_OFFSET = 60    # protrusion from side panel

# ── Build functions ───────────────────────────────────────────────────────────

def _make_wheel(r=40, h=30):
    """Simple caster wheel (cylinder)."""
    return cq.Workplane("XY").cylinder(h, r)


def make_hbm_tool_cart(
    width: float = CART_WIDTH,
    depth: float = CART_DEPTH,
    total_height: float = CART_TOTAL_HEIGHT,
    top_thickness: float = CART_TOP_THICKNESS,
    wheel_height: float = CART_WHEEL_HEIGHT,
    top_overhang: float = CART_TOP_OVERHANG,
) -> Assembly:
    """
    Return a CadQuery Assembly representing the HBM 146cm tool cart.

    Origin: floor-level centre of the cart footprint (X, Y) at Z=0.
    The cart extends:
        X: -width/2  … +width/2
        Y: -depth/2  … +depth/2
        Z: 0         … total_height
    """
    body_h  = total_height - top_thickness - wheel_height
    body_w  = width  - 2 * top_overhang
    body_d  = depth  - 2 * top_overhang

    assy = Assembly(name="hbm_tool_cart")

    # ── Cabinet body ─────────────────────────────────────────────────────────
    body = (
        cq.Workplane("XY")
        .box(body_w, body_d, body_h)
    )
    body_z = wheel_height + body_h / 2
    assy.add(
        body,
        name="body",
        color=Color("black"),
        loc=Location(Vector(0, 0, body_z)),
    )

    # ── Drawer faces (simplified flat rectangles on front face) ───────────────
    col_w  = body_w / 3
    row_h  = body_h / 10   # approximate even rows

    for col in range(3):
        for row in range(10):
            x_off = -body_w / 2 + col * col_w + col_w / 2
            z_off  = wheel_height + row * row_h + row_h / 2
            drawer_face = (
                cq.Workplane("XY")
                .box(col_w - 4, 4, row_h - 4)
            )
            assy.add(
                drawer_face,
                name=f"drawer_c{col}_r{row}",
                color=Color(0.3, 0.3, 0.3, 1.0),
                loc=Location(Vector(
                    x_off,
                    -body_d / 2 - 2,    # sits just proud of front face
                    z_off,
                )),
            )

    # ── Wood top ─────────────────────────────────────────────────────────────
    top = cq.Workplane("XY").box(width, depth, top_thickness)
    top_z = wheel_height + body_h + top_thickness / 2
    assy.add(
        top,
        name="wood_top",
        color=Color(0.76, 0.60, 0.35, 1.0),   # warm wood colour
        loc=Location(Vector(0, 0, top_z)),
    )

    # ── Wheels (6 casters) ───────────────────────────────────────────────────
    wheel_r  = 50
    wheel_h  = wheel_height - 20    # caster fork height above wheel
    wx_positions = [-body_w / 2 + 60, 0, body_w / 2 - 60]
    wy_positions = [-body_d / 2 + 50, body_d / 2 - 50]

    for i, wx in enumerate(wx_positions):
        for j, wy in enumerate(wy_positions):
            wheel = _make_wheel(r=wheel_r * 0.6, h=wheel_r * 1.0)
            assy.add(
                wheel,
                name=f"wheel_{i}_{j}",
                color=Color(0.2, 0.2, 0.2, 1.0),
                loc=Location(Vector(wx, wy, wheel_r * 0.5)),
            )

    # ── Side handle (right side, stainless tube) ─────────────────────────────
    handle_z  = wheel_height + body_h + 5   # just below wood top
    handle_x  = body_w / 2 + HANDLE_OFFSET
    handle    = (
        cq.Workplane("XZ")
        .center(handle_x, handle_z)
        .circle(HANDLE_R)
        .extrude(80)            # grip length
    )
    assy.add(
        handle,
        name="handle",
        color=Color(0.8, 0.8, 0.8, 1.0),   # stainless
        loc=Location(Vector(0, 0, 0)),
    )

    return assy


def get_bom() -> list[dict]:
    """Bill of materials / spec summary for documentation."""
    return [
        {
            "part": "HBM Gereedschapswagen 146cm (zwart)",
            "qty": 1,
            "width_mm": CART_WIDTH,
            "depth_mm": CART_DEPTH,
            "height_mm": CART_TOTAL_HEIGHT,
            "top_mm": CART_TOP_THICKNESS,
            "note": "Confirmed: width 1460mm, top 40mm. Estimated: depth 520mm, height 950mm.",
            "url": "https://www.hbm-machines.com/nl/p/hbm-verrijdbare-gereedschapswagen-met-houten-werkblad-146-cm-zwart",
        }
    ]


# ── Quick preview ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    assy = make_hbm_tool_cart()
    print("HBM Tool Cart assembly built successfully.")
    for item in get_bom():
        print(f"  {item['part']}")
        print(f"    {item['width_mm']} × {item['depth_mm']} × {item['height_mm']} mm")
        print(f"    ⚠  {item['note']}")
