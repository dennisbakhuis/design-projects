"""
HBM Verrijdbare Gereedschapswagen met Houten Werkblad — 146 cm (zwart)
CadQuery prop / helper object for workspace layout planning.

Product: https://www.hbm-machines.com/nl/p/hbm-verrijdbare-gereedschapswagen-met-houten-werkblad-146-cm-zwart
Artikelnummer: 4945  |  EAN: 7435125878907  |  Prijs: €699,99 incl. btw

── Confirmed dimensions (from product spec) ────────────────────────────────
  Outer (incl. wielen + handvat):  1610 × 460 × 920 mm  (L × B × H)
  Body only (excl. accessoires):   1465 × 460 × 770 mm
  Wielen diameter:  125 mm  |  breedte: 30 mm
  Wiel-hoogte (caster assembly):   920 - 770 = 150 mm
  Houten blad dikte: 40 mm
  Handvat-uitsteek:  1610 - 1465 = 145 mm (rechter zijkant)
  Gewicht: 125 kg  |  Max belasting: 750 kg  |  Laden: 20

── Lade-afmetingen (binnenwerk) ────────────────────────────────────────────
  Bovenste grote la:  400 × 960 × 100 mm  (D × B × H)
  Lade 1:  400 × 330 × 45 mm
  Lade 2:  400 × 330 × 150 mm
  Lade 3:  400 × 570 × 45 mm
  Lade 4:  400 × 570 × 150 mm
  Lade 5:  400 × 330 × 45 mm
  Lade 6:  400 × 330 × 200 mm

── Fit check werkbank (LEG_HEIGHT = 970 mm) ────────────────────────────────
  Hoogte kar: 920 mm  →  speling: 970 - 920 = 50 mm  ✓
  Lengte (body): 1465 mm  →  past in segment A (1845 mm vrij)  ✓
  Diepte: 460 mm  →  past onder werkbank (≥725 mm beschikbaar)  ✓
"""

import cadquery as cq
from cadquery import Assembly, Color, Location, Vector

# ── Parameters (all confirmed from product spec) ──────────────────────────────

CART_BODY_LENGTH    = 1465   # mm, cabinet body without handle
CART_TOTAL_LENGTH   = 1610   # mm, including side handle
CART_DEPTH          = 460    # mm
CART_TOTAL_HEIGHT   = 920    # mm, floor to top of wood surface
CART_BODY_HEIGHT_NO_WHEEL = 770   # mm, body without wheel assembly
CART_WHEEL_HEIGHT   = 150    # mm  (920 - 770)
CART_TOP_THICKNESS  = 40     # mm
CART_WHEEL_DIAM     = 125    # mm
CART_WHEEL_WIDTH    = 30     # mm
CART_HANDLE_EXT     = 145    # mm, handle extends beyond right end of body

# Derived
CART_BODY_HEIGHT    = CART_BODY_HEIGHT_NO_WHEEL  # excl. wheels = 770 mm
CART_TOP_OVERHANG   = (CART_TOTAL_LENGTH - CART_BODY_LENGTH) // 2  # ~22 mm each side
                      # (approximate — handle is right-side only, but top likely overhangs evenly)

# ── Drawer geometry (inner dimensions, confirmed) ─────────────────────────────
DRAWERS = [
    # name,               inner_depth, inner_width, inner_height
    ("top_large",          400, 960, 100),
    ("col_left_1_thin",    400, 330,  45),
    ("col_left_2_deep",    400, 330, 150),
    ("col_mid_3_thin",     400, 570,  45),
    ("col_mid_4_deep",     400, 570, 150),
    ("col_right_5_thin",   400, 330,  45),
    ("col_right_6_deep",   400, 330, 200),
]


# ── Build ─────────────────────────────────────────────────────────────────────

def _caster(wheel_diam: float, wheel_w: float, total_h: float):
    """
    Swivel caster: wheel (cylinder on its side, rotating around Y-axis)
    + mounting stem above it.
    wheel_diam = 125 mm, wheel_w = 30 mm (tread width), total_h = 150 mm
    """
    r = wheel_diam / 2
    # Wheel: cylinder rotating around Y-axis → extrude in Y, centred at wheel centre height
    wheel = (
        cq.Workplane("XZ")       # face in XZ plane → extrude along Y
        .circle(r)
        .extrude(wheel_w / 2, both=True)   # symmetric ±15 mm in Y
        .translate((0, 0, r))              # lift to z = r from floor
    )
    # Mounting fork/stem above wheel
    fork_h = total_h - wheel_diam
    fork = (
        cq.Workplane("XY")
        .box(20, wheel_w + 10, fork_h)
        .translate((0, 0, wheel_diam + fork_h / 2))
    )
    return wheel.union(fork)


def make_hbm_tool_cart(
    body_length:   float = CART_BODY_LENGTH,
    total_length:  float = CART_TOTAL_LENGTH,
    depth:         float = CART_DEPTH,
    total_height:  float = CART_TOTAL_HEIGHT,
    wheel_height:  float = CART_WHEEL_HEIGHT,
    top_thickness: float = CART_TOP_THICKNESS,
    handle_ext:    float = CART_HANDLE_EXT,
) -> Assembly:
    """
    Return a CadQuery Assembly for the HBM 146cm tool cart.

    Origin: floor-level centre of cart body footprint (X, Y) at Z=0.
    The BODY extends:
        X: -body_length/2  …  +body_length/2
        Y: -depth/2        …  +depth/2
        Z: 0               …  total_height
    The handle protrudes to +X beyond body_length/2.
    """
    body_h  = total_height - top_thickness - wheel_height  # metal cabinet = 730 mm
    wood_z  = wheel_height + body_h + top_thickness / 2
    body_z  = wheel_height + body_h / 2

    assy = Assembly(name="hbm_tool_cart")

    # ── Cabinet body (metal box) ──────────────────────────────────────────────
    body = cq.Workplane("XY").box(body_length, depth, body_h)
    assy.add(body, name="body", color=Color(0.08, 0.08, 0.08, 1.0),
             loc=Location(Vector(0, 0, body_z)))

    # ── Drawer layout ──────────────────────────────────────────────────────────
    # Top large drawer: full width, directly below wood top
    # Shaved 8mm top + 8mm bottom to avoid clipping with top and lower drawers
    top_la_h = 92    # was 108, reduced to avoid clipping
    top_la_z = wheel_height + body_h - top_la_h - 8  # 8mm gap below wood top
    top_la = cq.Workplane("XY").box(body_length - 10, 6, top_la_h)
    assy.add(top_la, name="drawer_top_large", color=Color(0.25, 0.25, 0.25, 1.0),
             loc=Location(Vector(0, -depth / 2 - 3, top_la_z + top_la_h / 2)))

    # 3 columns below the top drawer
    # Left: 330mm, Centre: 570mm, Right: 330mm  → ~1230mm total (fits within body)
    col_specs = [(-450, 330), (0, 570), (450, 330)]   # (x_centre, width)
    col_height = body_h - top_la_h                     # remaining height for 3 cols
    row_heights = [45, 150, 45, 150, 45, 200]          # 6 rows, ~635mm total

    z_cursor = wheel_height
    for row_idx, rh in enumerate(row_heights):
        for col_x, col_w in col_specs:
            face = cq.Workplane("XY").box(col_w - 6, 6, rh - 4)
            assy.add(
                face,
                name=f"drawer_r{row_idx}_cx{int(col_x)}",
                color=Color(0.25, 0.25, 0.25, 1.0),
                loc=Location(Vector(col_x, -depth / 2 - 3, z_cursor + rh / 2)),
            )
        z_cursor += rh

    # ── Wood top ──────────────────────────────────────────────────────────────
    # Top overhangs body slightly on all sides; extends full total_length in X
    top = cq.Workplane("XY").box(total_length - handle_ext, depth + 30, top_thickness)
    assy.add(top, name="wood_top", color=Color(0.72, 0.52, 0.30, 1.0),
             loc=Location(Vector(0, 0, wood_z)))

    # ── Casters (6 total: 4 corners + 2 middle) ──────────────────────────────
    corner_x = body_length / 2 - 60
    corner_y = depth / 2 - 40
    caster_positions = [
        (-corner_x, -corner_y), (-corner_x,  corner_y),   # left corners
        (       0,  -corner_y), (       0,   corner_y),    # middle pair
        ( corner_x, -corner_y), ( corner_x,  corner_y),   # right corners
    ]
    for i, (wx, wy) in enumerate(caster_positions):
        caster = _caster(CART_WHEEL_DIAM, CART_WHEEL_WIDTH, wheel_height)
        assy.add(caster, name=f"caster_{i}",
                 color=Color(0.15, 0.15, 0.15, 1.0),
                 loc=Location(Vector(wx, wy, 0)))

    # ── Handle: vertical D-loop on RIGHT END panel ───────────────────────────
    # Extends handle_ext mm beyond right end of body (+X direction)
    handle_z_bot = wheel_height + body_h * 0.50
    handle_z_top = wheel_height + body_h * 0.78
    handle_h     = handle_z_top - handle_z_bot
    grip_reach   = handle_ext

    arm_bottom = (
        cq.Workplane("YZ")
        .center(0, handle_z_bot)
        .circle(14)
        .extrude(grip_reach)
        .translate((body_length / 2, 0, 0))   # RIGHT side: +X
    )
    arm_top = (
        cq.Workplane("YZ")
        .center(0, handle_z_top)
        .circle(14)
        .extrude(grip_reach)
        .translate((body_length / 2, 0, 0))
    )
    grip = (
        cq.Workplane("XZ")
        .center(body_length / 2 + grip_reach, handle_z_bot + handle_h / 2)
        .circle(14)
        .extrude(200)
    )
    handle_shape = arm_bottom.union(arm_top).union(grip)
    assy.add(handle_shape, name="handle", color=Color(0.78, 0.78, 0.78, 1.0),
             loc=Location(Vector(0, 0, 0)))

    return assy


def get_bom() -> list[dict]:
    """Spec summary for documentation."""
    return [
        {
            "part": "HBM Gereedschapswagen 146cm (zwart) — art. 4945",
            "qty": 1,
            "length_body_mm": CART_BODY_LENGTH,
            "length_total_mm": CART_TOTAL_LENGTH,
            "depth_mm": CART_DEPTH,
            "height_mm": CART_TOTAL_HEIGHT,
            "wheel_height_mm": CART_WHEEL_HEIGHT,
            "top_thickness_mm": CART_TOP_THICKNESS,
            "weight_kg": 125,
            "max_load_kg": 750,
            "drawers": 20,
            "price_eur": 699.99,
            "url": "https://www.hbm-machines.com/nl/p/hbm-verrijdbare-gereedschapswagen-met-houten-werkblad-146-cm-zwart",
        }
    ]


# ── Top-level result for cq-editor / cq-designer ─────────────────────────────
result = make_hbm_tool_cart()


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    assy = make_hbm_tool_cart()
    item = get_bom()[0]
    print(f"HBM Tool Cart assembly built successfully.")
    print(f"  Body:   {item['length_body_mm']} × {item['depth_mm']} × {item['height_mm']} mm")
    print(f"  Total:  {item['length_total_mm']} mm (incl. handle)")
    print(f"  Wheels: {item['wheel_height_mm']} mm caster height")
    print(f"  Top:    {item['top_thickness_mm']} mm wood")
    print(f"  Weight: {item['weight_kg']} kg  |  Max load: {item['max_load_kg']} kg")
