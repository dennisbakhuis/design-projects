import sys
from pathlib import Path

import cadquery as cq
from cadquery import Assembly, Color, Location, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helper_objects import make_d12_twinset
from helper_objects.d12_twinset import CYLINDER_SPACING, TANK_DIAMETER
from helper_objects.hbm_tool_cart import make_hbm_tool_cart

# ── Design parameters ────────────────────────────────────────────────────────

TABLE_LENGTH = 2700
TABLE_WIDTH = 800
TABLE_THICKNESS = 52   # steamed beech 52 mm (per order)

LEG_WIDTH = 80  # oak timber 80×80 mm (per order)
LEG_DEPTH = 80
LEG_HEIGHT = 970

STRETCHER_WIDTH = 52  # steamed beech 52×75 mm (per order; ripped from 52×150)
STRETCHER_HEIGHT = 75
STRETCHER_INSET = 50
STRETCHER_Z = 150

APRON_HEIGHT = 75  # matches stretcher cross-section
APRON_THICKNESS = STRETCHER_WIDTH  # 50 mm, same as stretcher width

# ── Mortise & Tenon joint dimensions ────────────────────────────────────────
TENON_THICKNESS = 18   # mm  (from 50mm stock; 16mm shoulder each face)
TENON_HEIGHT    = 60   # mm  (from 75mm stock; 7.5mm shoulder top & bottom)
TENON_LENGTH    = 30   # mm  (depth into leg; leg is 75mm, leaves 45mm core)
MORTISE_DEPTH   = 32   # mm  (2mm clearance at bottom vs tenon length)

# D12 twinset arrangement: 3 columns x 2 rows = 6 twinsets / 12 tanks
TWINSET_COLS = 3
TWINSET_ROWS = 2

# ── Twinset front slat wall ───────────────────────────────────────────────
SLAT_WIDTH = 20  # face width of each slat (X direction), mm
SLAT_DEPTH = 15  # depth of each slat (Y direction), mm
SLAT_GAP = 10  # gap between slats, mm
SLAT_BOTTOM_Z = 20       # 2 cm above floor
SLAT_TOP_CLEARANCE = 10  # 1 cm below underside of top → slat = 970−20−10 = 940 mm
SLAT_WALL_INSET = 10     # how far inside the leg front face the slat wall sits, mm

EXT_DEPTH = 200
EXT_LENGTH = 800  # mm — widened from 780 to give 34mm clearance left of twinsets
FILLET_RADIUS = 100

# Wall beam parameters (mounts flush against the wall at back of table)
WALL_BEAM_WIDTH = 80   # oak timber 80×80 mm (per order)
WALL_BEAM_HEIGHT = 80  # depth into wall (Y)
WALL_BEAM_LENGTH = TABLE_LENGTH - 2 * STRETCHER_INSET  # inset on left and right sides

OUTPUT_DIR = Path(__file__).parent

# ── Main table leg positions ─────────────────────────────────────────────────
#
# The main table is a rectangle centered at the origin. One leg supports
# the front-left corner. The back is supported by a wall beam instead of
# legs. The front-right corner has no leg because the extension meets the
# table there.

leg_inset_x = STRETCHER_INSET + LEG_WIDTH / 2
leg_inset_y = STRETCHER_INSET + LEG_DEPTH / 2

left_x = -TABLE_LENGTH / 2 + leg_inset_x
right_x = TABLE_LENGTH / 2 - leg_inset_x
front_y = -TABLE_WIDTH / 2 + leg_inset_y
back_y = TABLE_WIDTH / 2 - leg_inset_y
wall_back_y = TABLE_WIDTH / 2 - LEG_DEPTH / 2  # back legs/beam flush against the wall

main_leg_positions = [
    ("front_left", left_x, front_y),
]

# ── Extension leg positions ──────────────────────────────────────────────────
#
# The extension protrudes from the front-right of the main table, creating an
# L-shaped top. It adds two legs along its front edge.

ext_front_y = -(TABLE_WIDTH / 2 + EXT_DEPTH)
ext_left_edge_x = TABLE_LENGTH / 2 - EXT_LENGTH

ext_leg_positions = [
    ("ext_front_right", right_x, ext_front_y + leg_inset_y),
    ("ext_front_left", ext_left_edge_x + leg_inset_x, ext_front_y + leg_inset_y),
]

# ── Derived dimensions ───────────────────────────────────────────────────────

APRON_Z = LEG_HEIGHT - APRON_HEIGHT / 2

main_span_x = abs(left_x - right_x)
main_span_y = abs(front_y - back_y)
wall_span_y = abs(front_y - wall_back_y)  # span from front leg to wall
wall_center_y = (front_y + wall_back_y) / 2  # midpoint between front leg and wall

ext_span_x = abs(ext_leg_positions[0][1] - ext_leg_positions[1][1])
ext_span_y = abs(back_y - ext_leg_positions[0][2])


# ── Geometry builders ────────────────────────────────────────────────────────


def box(length, width, height):
    """Create a centered box on the XY plane."""
    return cq.Workplane("XY").box(length, width, height)


def make_tabletop():
    """Build the L-shaped tabletop as a single filleted extrusion."""
    half_l = TABLE_LENGTH / 2
    half_w = TABLE_WIDTH / 2
    corner_x = half_l - EXT_LENGTH
    corner_y = -(half_w + EXT_DEPTH)

    result = (
        cq.Workplane("XY")
        .moveTo(half_l, half_w)
        .lineTo(-half_l, half_w)
        .lineTo(-half_l, -half_w)
        .lineTo(corner_x, -half_w)
        .lineTo(corner_x, corner_y)
        .lineTo(half_l, corner_y)
        .close()
        .extrude(TABLE_THICKNESS)
        .translate((0, 0, -TABLE_THICKNESS / 2))
    )

    inside_corner = (corner_x, -half_w, 0)
    return (
        result.edges("|Z")
        .edges(cq.selectors.NearestToPointSelector(inside_corner))
        .fillet(FILLET_RADIUS)
    )


def make_wall_beam():
    """Wall-mounted beam flush against the back wall.

    Inset on X sides by STRETCHER_INSET. 80 mm deep (Y) x 120 mm tall (Z).
    """
    return cq.Workplane("XY").box(WALL_BEAM_LENGTH, WALL_BEAM_HEIGHT, WALL_BEAM_WIDTH)


def loc(x, y, z):
    return Location(Vector(x, y, z))


def slat_wall_positions(total_width: float) -> list[float]:
    """Return X offsets (relative to wall center) for each slat center."""
    pitch = SLAT_WIDTH + SLAT_GAP
    n_slats = int(total_width // pitch)
    array_width = n_slats * pitch - SLAT_GAP
    x_start = -array_width / 2 + SLAT_WIDTH / 2
    return [x_start + i * pitch for i in range(n_slats)]


# ── Stretcher & apron specs ──────────────────────────────────────────────────
#
# Each entry: (name, length_x, length_y, x, y, z)
# Stretchers run between legs at the bottom; aprons sit just under the tabletop.

main_stretchers = [
    ("left", STRETCHER_WIDTH, wall_span_y - LEG_DEPTH, left_x, wall_center_y, STRETCHER_Z),
]

main_aprons = [
    ("left", APRON_THICKNESS, wall_span_y + LEG_DEPTH, left_x, wall_center_y, APRON_Z),
]

ext_mid_x = (ext_leg_positions[0][1] + ext_leg_positions[1][1]) / 2
ext_front_leg_y = ext_leg_positions[0][2]
ext_left_leg_x = ext_left_edge_x + leg_inset_x  # X of ext back-left leg

# ext_left stretcher/apron now spans from ext_front_left leg to wall_back_y
ext_left_span_y = abs(wall_back_y - ext_front_leg_y)
ext_left_center_y = (wall_back_y + ext_front_leg_y) / 2

# ext_front stretcher/apron mid-points (unchanged, use for ext_front members)
ext_stretcher_mid_y = (back_y + ext_front_leg_y - LEG_DEPTH / 2) / 2
ext_apron_mid_y = (back_y + ext_front_leg_y + LEG_DEPTH / 2) / 2

ext_stretchers = [
    (
        "ext_left",
        STRETCHER_WIDTH,
        ext_left_span_y - LEG_DEPTH,
        ext_left_leg_x + LEG_WIDTH / 2 - STRETCHER_WIDTH / 2,
        ext_left_center_y,
        STRETCHER_Z,
    ),
]

ext_aprons = [
    (
        "ext_left",
        APRON_THICKNESS,
        ext_left_span_y + LEG_DEPTH,
        ext_left_leg_x + LEG_WIDTH / 2 - APRON_THICKNESS / 2,
        ext_left_center_y,
        APRON_Z,
    ),
]

# ── Combined leg position lists (used by get_bom / make_workbench_stage) ─────

leg_positions = main_leg_positions + ext_leg_positions  # floor legs (not wall)

wall_leg_positions = [
    ("wall_back_left", left_x, wall_back_y),
    ("wall_back_right", right_x, wall_back_y),
    ("ext_back_left", ext_left_leg_x, wall_back_y),
]


# ── Bill of Materials ─────────────────────────────────────────────────────────


def get_bom():
    """Return bill of materials as a list of dicts with keys:
    part, material, qty, width_mm, depth_mm, length_mm, note
    """
    total_legs = len(leg_positions) + len(wall_leg_positions)

    # Stretcher/apron lengths — compute from geometry
    main_left_span = abs(wall_back_y - ext_front_leg_y) - LEG_DEPTH
    front_rail_span = (right_x - LEG_WIDTH / 2) - (ext_left_leg_x + LEG_WIDTH / 2)
    right_rail_span = abs(wall_back_y - LEG_DEPTH / 2 - (ext_front_leg_y + LEG_DEPTH / 2))

    # Slat counts
    slat_height = LEG_HEIGHT - SLAT_BOTTOM_Z - SLAT_TOP_CLEARANCE  # 940 mm
    front_wall_span = (right_x - LEG_WIDTH / 2) - (ext_left_leg_x + LEG_WIDTH / 2)
    n_front_slats = int(front_wall_span // (SLAT_WIDTH + SLAT_GAP))
    side_wall_span = (wall_back_y - LEG_DEPTH / 2) - (ext_front_leg_y + LEG_DEPTH / 2)
    n_side_slats = int(side_wall_span // (SLAT_WIDTH + SLAT_GAP))

    return [
        # Legs
        {
            "part": f"Leg {LEG_WIDTH}×{LEG_DEPTH}mm",
            "material": "Oak timber",
            "qty": total_legs,
            "width_mm": LEG_WIDTH,
            "depth_mm": LEG_DEPTH,
            "length_mm": LEG_HEIGHT,
            "note": "All structural legs",
        },
        # Main left stretcher
        {
            "part": f"Stretcher {STRETCHER_WIDTH}×75mm — left side",
            "material": "Steamed beech",
            "qty": 1,
            "width_mm": STRETCHER_WIDTH,
            "depth_mm": STRETCHER_HEIGHT,
            "length_mm": round(main_left_span),
            "note": "Front-left to wall, bottom rail",
        },
        # ext_left stretcher
        {
            "part": f"Stretcher {STRETCHER_WIDTH}×75mm — ext. left",
            "material": "Steamed beech",
            "qty": 1,
            "width_mm": STRETCHER_WIDTH,
            "depth_mm": STRETCHER_HEIGHT,
            "length_mm": round(ext_left_span_y - LEG_DEPTH),
            "note": "Ext. left side, bottom rail",
        },
        # Main left apron
        {
            "part": f"Apron {APRON_THICKNESS}×75mm — left side",
            "material": "Steamed beech",
            "qty": 1,
            "width_mm": APRON_THICKNESS,
            "depth_mm": APRON_HEIGHT,
            "length_mm": round(main_left_span),
            "note": "Front-left to wall, top rail",
        },
        # ext_left apron
        {
            "part": f"Apron {APRON_THICKNESS}×75mm — ext. left",
            "material": "Steamed beech",
            "qty": 1,
            "width_mm": APRON_THICKNESS,
            "depth_mm": APRON_HEIGHT,
            "length_mm": round(ext_left_span_y + LEG_DEPTH),
            "note": "Ext. left side, top rail",
        },
        # Wall beam
        {
            "part": f"Wall beam {WALL_BEAM_WIDTH}×{WALL_BEAM_HEIGHT}mm",
            "material": "Oak timber",
            "qty": 1,
            "width_mm": WALL_BEAM_WIDTH,
            "depth_mm": WALL_BEAM_HEIGHT,
            "length_mm": WALL_BEAM_LENGTH,
            "note": "Wall-mounted rear beam; lag screws into wall",
        },
        # Twinset front mounting rails (bottom + top)
        {
            "part": f"Mounting rail {STRETCHER_WIDTH}×75mm — front",
            "material": "Steamed beech",
            "qty": 2,
            "width_mm": STRETCHER_WIDTH,
            "depth_mm": STRETCHER_HEIGHT,
            "length_mm": round(front_rail_span),
            "note": "Bottom + top rail for front slat wall",
        },
        # Right side top rail
        {
            "part": f"Rail {STRETCHER_WIDTH}×75mm — right side top",
            "material": "Steamed beech",
            "qty": 1,
            "width_mm": STRETCHER_WIDTH,
            "depth_mm": STRETCHER_HEIGHT,
            "length_mm": round(right_rail_span),
            "note": "Top rail, right side twinset enclosure",
        },
        # Tabletop
        {
            "part": "Tabletop (L-shape)",
            "material": f"Steamed beech {TABLE_THICKNESS}mm (edge-glued)",
            "qty": 1,
            "width_mm": TABLE_LENGTH,
            "depth_mm": TABLE_WIDTH + EXT_DEPTH,
            "length_mm": TABLE_THICKNESS,
            "note": f"L-shape {TABLE_LENGTH}×{TABLE_WIDTH}mm + ext. {EXT_LENGTH}×{EXT_DEPTH}mm — see drawing",
        },
        # Front slats
        {
            "part": "Slat 20×15mm — front wall",
            "material": "Solid timber",
            "qty": n_front_slats,
            "width_mm": SLAT_WIDTH,
            "depth_mm": SLAT_DEPTH,
            "length_mm": round(slat_height),
            "note": "Decorative front slat panel",
        },
        # Side slats
        {
            "part": "Slat 20×15mm — left side wall",
            "material": "Solid timber",
            "qty": n_side_slats,
            "width_mm": SLAT_WIDTH,
            "depth_mm": SLAT_DEPTH,
            "length_mm": round(slat_height),
            "note": "Decorative left-side slat panel",
        },
        # Hardware
        {
            "part": "Pocket screws 50mm",
            "material": "Steel",
            "qty": 60,
            "width_mm": None,
            "depth_mm": None,
            "length_mm": 50,
            "note": "Leg-to-apron/stretcher joints (~4 per joint)",
        },
        {
            "part": "Lag screw M10×120mm",
            "material": "Steel (hot-dip galv.)",
            "qty": 6,
            "width_mm": None,
            "depth_mm": None,
            "length_mm": 120,
            "note": "Wall beam to masonry/stud wall",
        },
        {
            "part": "Wood screw 3.5×35mm",
            "material": "Steel",
            "qty": n_front_slats * 4 + n_side_slats * 4,
            "width_mm": None,
            "depth_mm": None,
            "length_mm": 35,
            "note": "Slat to mounting rail (2 per end per slat)",
        },
    ]


# ── Staged assembly (IKEA-style manual) ───────────────────────────────────────


def make_workbench_stage(stage: int) -> cq.Assembly:
    """Build a partial assembly for IKEA-style manual illustrations.

    Stages:
      0 — legs only
      1 — legs + stretchers
      2 — legs + stretchers + aprons + wall beam
      3 — add tabletop
      4 — add slat mounting rails
      5 — full assembly (slats included, no props)
    """
    assy = cq.Assembly(name="workbench_stage")

    # ── Legs ────────────────────────────────────────────────────────────
    for name, lx, ly in leg_positions:
        assy.add(
            box(LEG_WIDTH, LEG_DEPTH, LEG_HEIGHT),
            name=name,
            loc=loc(lx, ly, LEG_HEIGHT / 2),
            color=Color("saddlebrown"),
        )
    for name, lx, ly in wall_leg_positions:
        assy.add(
            box(LEG_WIDTH, LEG_DEPTH, LEG_HEIGHT),
            name=name,
            loc=loc(lx, ly, LEG_HEIGHT / 2),
            color=Color("saddlebrown"),
        )
    if stage < 1:
        return assy

    # ── Stretchers ──────────────────────────────────────────────────────
    for name, lx, ly, x, y, z in main_stretchers:
        assy.add(box(lx, ly, STRETCHER_HEIGHT), name=f"s_{name}", loc=loc(x, y, z), color=Color("burlywood"))
    for name, lx, ly, x, y, z in ext_stretchers:
        assy.add(box(lx, ly, STRETCHER_HEIGHT), name=f"se_{name}", loc=loc(x, y, z), color=Color("burlywood"))
    if stage < 2:
        return assy

    # ── Aprons + wall beam ───────────────────────────────────────────────
    for name, lx, ly, x, y, z in main_aprons:
        assy.add(box(lx, ly, APRON_HEIGHT), name=f"a_{name}", loc=loc(x, y, z), color=Color("burlywood"))
    for name, lx, ly, x, y, z in ext_aprons:
        assy.add(box(lx, ly, APRON_HEIGHT), name=f"ae_{name}", loc=loc(x, y, z), color=Color("burlywood"))
    wall_beam_x = (right_x + left_x) / 2
    wall_beam_len = TABLE_LENGTH - 2 * STRETCHER_INSET
    assy.add(
        box(wall_beam_len, LEG_DEPTH, LEG_WIDTH),
        name="wall_beam",
        loc=loc(wall_beam_x, wall_back_y, APRON_Z),
        color=Color("saddlebrown"),
    )
    if stage < 3:
        return assy

    # ── Tabletop ─────────────────────────────────────────────────────────
    assy.add(
        make_tabletop(),
        name="tabletop",
        loc=loc(0, 0, LEG_HEIGHT + TABLE_THICKNESS / 2),
        color=Color("wheat"),
    )
    if stage < 4:
        return assy

    # ── Slat mounting rails ───────────────────────────────────────────────
    rail_y = ext_front_leg_y + LEG_DEPTH / 2 - STRETCHER_WIDTH / 2
    front_slat_x_left = ext_left_leg_x + LEG_WIDTH / 2
    front_slat_x_right = right_x - LEG_WIDTH / 2
    front_rail_span = front_slat_x_right - front_slat_x_left
    front_rail_mid_x = (front_slat_x_left + front_slat_x_right) / 2
    assy.add(box(front_rail_span, STRETCHER_WIDTH, STRETCHER_HEIGHT), name="front_rail_bot",
             loc=loc(front_rail_mid_x, rail_y, STRETCHER_Z), color=Color("peru"))
    assy.add(box(front_rail_span, STRETCHER_WIDTH, APRON_HEIGHT), name="front_rail_top",
             loc=loc(front_rail_mid_x, rail_y, APRON_Z), color=Color("peru"))
    right_rail_x = right_x - LEG_WIDTH / 2 + STRETCHER_WIDTH / 2
    side_y_front = ext_front_leg_y + LEG_DEPTH / 2
    side_y_back = wall_back_y - LEG_DEPTH / 2
    right_rail_span = side_y_back - side_y_front
    right_rail_cy = (side_y_front + side_y_back) / 2
    assy.add(box(STRETCHER_WIDTH, right_rail_span, APRON_HEIGHT), name="right_rail_top",
             loc=loc(right_rail_x, right_rail_cy, APRON_Z), color=Color("peru"))
    if stage < 5:
        return assy

    # ── Slats ─────────────────────────────────────────────────────────────
    # Slats: 2cm above floor → 1cm below tabletop underside (screw to mounting rails)
    slat_height = LEG_HEIGHT - SLAT_BOTTOM_Z - SLAT_TOP_CLEARANCE  # 940 mm
    slat_z_ctr  = SLAT_BOTTOM_Z + slat_height / 2

    side_slat_x = ext_left_leg_x - LEG_WIDTH / 2 + SLAT_WALL_INSET + SLAT_DEPTH / 2
    # Position slats in FRONT of mounting rails (same formula as make_workbench)
    front_slat_wall_y = ext_front_y + STRETCHER_INSET + SLAT_WALL_INSET + SLAT_DEPTH / 2

    slat_x_left = ext_left_leg_x + LEG_WIDTH / 2
    slat_x_right = right_x - LEG_WIDTH / 2
    front_span = slat_x_right - slat_x_left
    pitch = SLAT_WIDTH + SLAT_GAP
    n_f = int(front_span // pitch)
    arr_span_f = n_f * pitch - SLAT_GAP
    x0 = (slat_x_left + slat_x_right) / 2 - arr_span_f / 2 + SLAT_WIDTH / 2
    for i in range(n_f):
        assy.add(box(SLAT_WIDTH, SLAT_DEPTH, slat_height), name=f"fs_{i}",
                 loc=loc(x0 + i * pitch, front_slat_wall_y, SLAT_BOTTOM_Z + slat_height / 2),
                 color=Color("burlywood"))

    side_wall_y_front = ext_front_leg_y + LEG_DEPTH / 2
    side_wall_y_back = wall_back_y - LEG_DEPTH / 2
    side_span = side_wall_y_back - side_wall_y_front
    side_cy = (side_wall_y_front + side_wall_y_back) / 2
    n_s = int(side_span // pitch)
    arr_span_s = n_s * pitch - SLAT_GAP
    y0 = side_cy - arr_span_s / 2 + SLAT_WIDTH / 2
    for i in range(n_s):
        assy.add(box(SLAT_DEPTH, SLAT_WIDTH, slat_height), name=f"ss_{i}",
                 loc=loc(side_slat_x, y0 + i * pitch, SLAT_BOTTOM_Z + slat_height / 2),
                 color=Color("burlywood"))

    return assy


# ── Assembly ─────────────────────────────────────────────────────────────────


def make_workbench(include_props: bool = True):
    """Assemble the complete workbench with legs, stretchers, and aprons.

    Returns
    -------
    cq.Assembly
        The full workbench assembly.
    """
    assy = Assembly(name="workbench")

    assy.add(
        make_tabletop(),
        name="tabletop",
        loc=loc(0, 0, LEG_HEIGHT + TABLE_THICKNESS / 2),
        color=Color("burlywood"),
    )

    for label, x, y in main_leg_positions + ext_leg_positions:
        assy.add(
            box(LEG_WIDTH, LEG_DEPTH, LEG_HEIGHT),
            name=f"leg_{label}",
            loc=loc(x, y, LEG_HEIGHT / 2),
            color=Color("peru"),
        )

    # ── Wall legs (back-left, back-right, ext-back-left — floor-to-ceiling) ──
    for label, x in [
        ("wall_back_left", left_x),
        ("wall_back_right", right_x),
        ("ext_back_left", ext_left_leg_x),
    ]:
        assy.add(
            box(LEG_WIDTH, LEG_DEPTH, LEG_HEIGHT),
            name=f"leg_{label}",
            loc=loc(x, wall_back_y, LEG_HEIGHT / 2),
            color=Color("peru"),
        )

    for label, lx, ly, x, y, z in main_stretchers + ext_stretchers:
        assy.add(
            box(lx, ly, STRETCHER_HEIGHT),
            name=f"stretcher_{label}",
            loc=loc(x, y, z),
            color=Color("sienna"),
        )

    for label, lx, ly, x, y, z in main_aprons + ext_aprons:
        assy.add(
            box(lx, ly, APRON_HEIGHT),
            name=f"apron_{label}",
            loc=loc(x, y, z),
            color=Color("saddlebrown"),
        )

    # ── Wall beam (replaces back_left and back_right legs) ────────────────
    assy.add(
        make_wall_beam(),
        name="wall_beam",
        loc=loc(0, wall_back_y, APRON_Z),
        color=Color(0.4, 0.4, 0.4),
    )

    if include_props:
        # ── HBM tool cart — stored in segment A (left section under bench) ────
        # Segment A inner X span: left_x+LEG_WIDTH/2  →  ext_left_leg_x-LEG_WIDTH/2
        #   = -1225 mm  →  +620 mm  (1845 mm wide)
        # Cart body 1465 mm centred at x = (-1225+620)/2 = -302.5 mm
        # Cart pushed to back: Y centre = (wall_back_y - LEG_DEPTH/2) - 460/2
        cart_x = (left_x + LEG_WIDTH / 2 + ext_left_leg_x - LEG_WIDTH / 2) / 2   # -302.5 mm
        cart_y = -TABLE_WIDTH / 2 + 50 + 460 / 2                                   # front face 50mm inset = -120 mm
        assy.add(
            make_hbm_tool_cart(),
            name="tool_cart",
            loc=Location(Vector(cart_x, cart_y, 0)),
        )

        # ── D12 twinsets: 3 columns x 2 rows = 6 twinsets / 12 tanks ─────────
        # Twinsets are rotated 90° around Z so cylinders are side-by-side in Y.
        # Anchored to the back-right corner; back row is closest to the wall.
        column_spacing = TANK_DIAMETER + 30  # 202 mm per column
        row_spacing = (
            CYLINDER_SPACING + TANK_DIAMETER + 30
        )  # 405 mm per row (full twinset Y footprint + gap)

        for row in range(TWINSET_ROWS):
            for col in range(TWINSET_COLS):
                tx = (right_x + LEG_WIDTH / 2 - 10 - TANK_DIAMETER / 2) - col * column_spacing
                ty = (back_y - CYLINDER_SPACING / 2 - TANK_DIAMETER / 2) - row * row_spacing
                assy.add(
                    make_d12_twinset(),
                    name=f"d12_twinset_{row}_{col}",
                    loc=Location(Vector(tx, ty, 0), Vector(0, 0, 1), 90),
                )

    # ── Twinset front slat wall ───────────────────────────────────────────
    column_spacing_val = TANK_DIAMETER + 30  # must match the twinset loop value
    row_spacing_val = CYLINDER_SPACING + TANK_DIAMETER + 30

    # X extent: between the inner faces of the extension legs (no clipping)
    slat_wall_x_right = right_x - LEG_WIDTH / 2          # inner face of ext_front_right leg
    slat_wall_x_left = ext_left_leg_x + LEG_WIDTH / 2    # inner face of ext_front_left leg
    slat_wall_width = slat_wall_x_right - slat_wall_x_left
    slat_wall_center_x = (slat_wall_x_right + slat_wall_x_left) / 2

    # Y position: slightly inside the extension leg front face
    # Leg front face is at ext_front_y + STRETCHER_INSET; slat sits SLAT_WALL_INSET mm behind it
    slat_wall_y = ext_front_y + STRETCHER_INSET + SLAT_WALL_INSET + SLAT_DEPTH / 2

    slat_height = LEG_HEIGHT - SLAT_BOTTOM_Z - SLAT_TOP_CLEARANCE  # 940 mm
    slat_z_ctr  = SLAT_BOTTOM_Z + slat_height / 2

    for i, x_offset in enumerate(slat_wall_positions(slat_wall_width)):
        assy.add(
            box(SLAT_WIDTH, SLAT_DEPTH, slat_height),
            name=f"slat_{i}",
            loc=loc(slat_wall_center_x + x_offset, slat_wall_y, slat_z_ctr),
            color=Color("burlywood"),
        )

    # ── Twinset front mounting rails (slats attach to these) ─────────────
    # Positioned just behind the slat wall back face, spanning the same X extent.
    # Mounting rails flush with the inner (back) face of the extension front legs.
    # Stretcher back face = leg back face → no clipping with slat wall.
    rail_y = ext_front_leg_y + LEG_DEPTH / 2 - STRETCHER_WIDTH / 2
    assy.add(
        box(slat_wall_width, STRETCHER_WIDTH, STRETCHER_HEIGHT),
        name="twinset_front_rail_bottom",
        loc=loc(slat_wall_center_x, rail_y, STRETCHER_Z),
        color=Color("sienna"),
    )
    assy.add(
        box(slat_wall_width, APRON_THICKNESS, APRON_HEIGHT),
        name="twinset_front_rail_top",
        loc=loc(slat_wall_center_x, rail_y, APRON_Z),
        color=Color("saddlebrown"),
    )

    # ── Twinset left side slat wall ───────────────────────────────────────
    # Runs in Y (front to back), visible from the left when facing the workbench.
    # Slat outer face is SLAT_WALL_INSET inside the left leg outer face.
    side_slat_x = ext_left_leg_x - LEG_WIDTH / 2 + SLAT_WALL_INSET + SLAT_DEPTH / 2

    # Y span: between inner faces of front and back legs
    side_wall_y_front = ext_front_leg_y + LEG_DEPTH / 2   # inner face of front leg
    side_wall_y_back = wall_back_y - LEG_DEPTH / 2        # inner face of back leg
    side_wall_span_y = side_wall_y_back - side_wall_y_front
    side_wall_center_y = (side_wall_y_front + side_wall_y_back) / 2

    slat_pitch = SLAT_WIDTH + SLAT_GAP
    n_side_slats = int(side_wall_span_y // slat_pitch)
    side_array_span = n_side_slats * slat_pitch - SLAT_GAP
    side_y_start = side_wall_center_y - side_array_span / 2 + SLAT_WIDTH / 2

    for i in range(n_side_slats):
        sy = side_y_start + i * slat_pitch
        assy.add(
            box(SLAT_DEPTH, SLAT_WIDTH, slat_height),
            name=f"side_slat_{i}",
            loc=loc(side_slat_x, sy, SLAT_BOTTOM_Z + slat_height / 2),
            color=Color("burlywood"),
        )

    # ── Top stretcher — right side of twinset enclosure ──────────────────
    # Runs in Y, flush with inner (left) face of right leg, at apron height.
    right_rail_x = right_x - LEG_WIDTH / 2 + STRETCHER_WIDTH / 2
    right_rail_span = side_wall_y_back - side_wall_y_front
    right_rail_center_y = (side_wall_y_front + side_wall_y_back) / 2
    assy.add(
        box(STRETCHER_WIDTH, right_rail_span, APRON_HEIGHT),
        name="twinset_right_top_rail",
        loc=loc(right_rail_x, right_rail_center_y, APRON_Z),
        color=Color("saddlebrown"),
    )

    return assy


# ── Viewer support (CQ-editor / CQ-designer) ────────────────────────────────

result = make_workbench()

# ── CLI: export views when run directly ──────────────────────────────────────

if __name__ == "__main__" and "--svg" in sys.argv:
    compound = result.toCompound()

    def rotated(shape, axis, angle):
        return shape.rotate((0, 0, 0), axis, angle)

    stem = Path(__file__).stem

    def export_view(comp, view, width=1600, height=1000):
        cq.exporters.export(
            comp,
            str(OUTPUT_DIR / f"{stem}_{view}.svg"),
            opt={
                "projectionDir": (0, 0, 1),
                "width": width,
                "height": height,
                "showAxes": False,
                "strokeColor": (40, 40, 40),
                "hiddenColor": (200, 200, 200),
                "showHidden": False,
            },
        )

    export_view(compound, "top")
    export_view(rotated(compound, (-1, 0, 0), 90), "front")
    export_view(rotated(rotated(compound, (-1, 0, 0), 90), (0, -1, 0), 90), "side")

    threed = rotated(compound, (-1, 0, 0), 75)
    threed = rotated(threed, (0, 1, 0), -40)
    export_view(threed, "3d")
