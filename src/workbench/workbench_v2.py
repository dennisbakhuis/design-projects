import sys
from pathlib import Path

import cadquery as cq
from cadquery import Assembly, Color, Location, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helper_objects import make_d12_twinset
from helper_objects.d12_tanks.d12_tanks import CYLINDER_SPACING, TANK_DIAMETER

# ── Design parameters ────────────────────────────────────────────────────────

TABLE_LENGTH = 2700
TABLE_WIDTH = 800
TABLE_THICKNESS = 40

LEG_WIDTH = 75   # standard 75×75 mm planed timber
LEG_DEPTH = 75
LEG_HEIGHT = 960

STRETCHER_WIDTH = 50   # standard 50×75 mm planed timber
STRETCHER_HEIGHT = 75
STRETCHER_INSET = 50
STRETCHER_Z = 150

APRON_HEIGHT = 75      # matches stretcher cross-section
APRON_THICKNESS = STRETCHER_WIDTH  # 50 mm, same as stretcher width

# D12 twinset arrangement: 3 columns × 2 rows = 6 twinsets / 12 tanks
TWINSET_COLS = 3
TWINSET_ROWS = 2

EXT_DEPTH = 200
EXT_LENGTH = 750  # TWINSET_COLS * (200 + 50) - 50 + STRETCHER_INSET
FILLET_RADIUS = 100

# Wall beam parameters (mounts flush against the wall at back of table)
WALL_BEAM_WIDTH = 75   # standard 75×75 mm planed timber (height, Z)
WALL_BEAM_HEIGHT = 75  # depth into wall (Y)
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

    Inset on X sides by STRETCHER_INSET. 80 mm deep (Y) × 120 mm tall (Z).
    """
    return cq.Workplane("XY").box(WALL_BEAM_LENGTH, WALL_BEAM_HEIGHT, WALL_BEAM_WIDTH)


def loc(x, y, z):
    return Location(Vector(x, y, z))


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
    ("ext_front", ext_span_x - LEG_WIDTH, STRETCHER_WIDTH, ext_mid_x, ext_front_leg_y, STRETCHER_Z),
    (
        "ext_left",
        STRETCHER_WIDTH,
        ext_left_span_y - LEG_DEPTH,
        ext_left_leg_x,
        ext_left_center_y,
        STRETCHER_Z,
    ),
]

ext_aprons = [
    ("ext_front", ext_span_x + LEG_WIDTH, APRON_THICKNESS, ext_mid_x, ext_front_leg_y, APRON_Z),
    (
        "ext_left",
        APRON_THICKNESS,
        ext_left_span_y + LEG_DEPTH,
        ext_left_leg_x,
        ext_left_center_y,
        APRON_Z,
    ),
]

# ── Assembly ─────────────────────────────────────────────────────────────────


def make_workbench():
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

    # ── D12 twinsets: 3 columns × 2 rows = 6 twinsets / 12 tanks ─────────
    # Twinsets are rotated 90° around Z so cylinders are side-by-side in Y.
    # Anchored to the back-right corner; back row is closest to the wall.
    column_spacing = TANK_DIAMETER + 30       # 202 mm per column
    row_spacing = CYLINDER_SPACING + TANK_DIAMETER + 30   # 405 mm per row (full twinset Y footprint + gap)

    for row in range(TWINSET_ROWS):
        for col in range(TWINSET_COLS):
            tx = (right_x + LEG_WIDTH / 2 - 10 - TANK_DIAMETER / 2) - col * column_spacing
            ty = (back_y - CYLINDER_SPACING / 2 - TANK_DIAMETER / 2) - row * row_spacing
            assy.add(
                make_d12_twinset(),
                name=f"d12_twinset_{row}_{col}",
                loc=Location(Vector(tx, ty, 0), Vector(0, 0, 1), 90),
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
