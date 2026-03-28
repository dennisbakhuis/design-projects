"""D12 diving cylinder twinset — CadQuery model."""

import cadquery as cq
from cadquery import Assembly, Color, Location, Vector

# ── D12 cylinder dimensions ──────────────────────────────────────────────────

TANK_DIAMETER = 172
TANK_RADIUS = TANK_DIAMETER / 2
TANK_BODY_HEIGHT = 550
TANK_DOME_HEIGHT = 45
TANK_TOTAL_HEIGHT = TANK_BODY_HEIGHT + 2 * TANK_DOME_HEIGHT

# ── Valve & manifold ─────────────────────────────────────────────────────────
# Each post valve sits on the tank neck. The knob angles outward and upward
# (~35 deg from horizontal). The manifold bar connects the two valve bodies
# with an isolator valve knob pointing upward from the center.

VALVE_NECK_DIAMETER = 40
VALVE_NECK_HEIGHT = 30
VALVE_BODY_LENGTH = 60
VALVE_BODY_WIDTH = 45
VALVE_BODY_HEIGHT = 45
VALVE_KNOB_DIAMETER = 32
VALVE_KNOB_LENGTH = 45
VALVE_KNOB_ANGLE = 0
DIN_PORT_DIAMETER = 38
DIN_PORT_DEPTH = 15

MANIFOLD_BAR_WIDTH = 22
MANIFOLD_BAR_HEIGHT = 22
ISOLATOR_KNOB_DIAMETER = 32
ISOLATOR_KNOB_LENGTH = 40

# ── Band clamps (V4TEC style) ────────────────────────────────────────────────
# Two sets of rings around each cylinder, connected by a flat piece between
# the tanks. An M8 threaded rod runs through the center hole between the
# tanks, sticking out on one side.

BAND_WIDTH = 60
BAND_THICKNESS = 3
BAND_FLAT_WIDTH = 20
BAND_FLAT_THICKNESS = 3
BAND_HOLE_SPACING = 279
BAND_TOP_Z = 530
BAND_POSITIONS = [BAND_TOP_Z, BAND_TOP_Z - BAND_HOLE_SPACING]

M8_ROD_DIAMETER = 8
M8_ROD_PROTRUSION = TANK_RADIUS - 25

# ── Twin-set spacing ─────────────────────────────────────────────────────────
# Bolt spacing (center-to-center) is 203mm for GUE manifold.

CYLINDER_SPACING = 203
CYLINDER_GAP = CYLINDER_SPACING - TANK_DIAMETER

COLOR_STEEL = Color(0.86, 0.86, 0.86)
COLOR_CHROME = Color(0.75, 0.75, 0.75)
COLOR_BLACK = Color(0.12, 0.12, 0.12)


def loc(x, y, z):
    return Location(Vector(x, y, z))


# ── Single cylinder ──────────────────────────────────────────────────────────


def make_tank_body():
    """Cylindrical body with rounded top and bottom domes."""
    body = cq.Workplane("XY").circle(TANK_RADIUS).extrude(TANK_BODY_HEIGHT)

    dome = (
        cq.Workplane("XZ")
        .center(0, 0)
        .moveTo(0, 0)
        .lineTo(TANK_RADIUS, 0)
        .threePointArc((TANK_RADIUS * 0.7, TANK_DOME_HEIGHT), (0, TANK_DOME_HEIGHT))
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )

    body = body.union(dome.translate((0, 0, TANK_BODY_HEIGHT)))
    body = body.union(dome.mirror("XY"))
    return body


# ── Post valve (left or right) ───────────────────────────────────────────────


def make_post_valve(side="left"):
    """Post valve with neck, body, angled knob, and DIN port.

    Parameters
    ----------
    side : str
        "left" or "right" — determines knob direction.
    """
    sign = -1 if side == "left" else 1

    neck = cq.Workplane("XY").circle(VALVE_NECK_DIAMETER / 2).extrude(VALVE_NECK_HEIGHT)

    body_z = VALVE_NECK_HEIGHT
    body_center_z = body_z + VALVE_BODY_HEIGHT / 2
    body = (
        cq.Workplane("XY")
        .box(VALVE_BODY_LENGTH, VALVE_BODY_WIDTH, VALVE_BODY_HEIGHT)
        .translate((0, 0, body_center_z))
    )

    knob = (
        cq.Workplane("XY")
        .circle(VALVE_KNOB_DIAMETER / 2)
        .extrude(VALVE_KNOB_LENGTH)
        .translate((0, 0, VALVE_BODY_WIDTH / 2))
        .rotate((0, 0, 0), (0, 1, 0), sign * (90 - VALVE_KNOB_ANGLE))
        .translate((0, 0, body_center_z))
    )

    din_port = (
        cq.Workplane("XY")
        .circle(DIN_PORT_DIAMETER / 2)
        .extrude(DIN_PORT_DEPTH)
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((0, -VALVE_BODY_WIDTH / 2, body_center_z))
    )

    return neck.union(body).union(knob).union(din_port)


# ── Manifold ─────────────────────────────────────────────────────────────────


def make_manifold_bar():
    """Horizontal bar connecting the two valves."""
    return cq.Workplane("XY").box(CYLINDER_SPACING, MANIFOLD_BAR_WIDTH, MANIFOLD_BAR_HEIGHT)


def make_isolator_knob():
    """Upward-pointing isolator knob for center of manifold."""
    return (
        cq.Workplane("XY")
        .circle(ISOLATOR_KNOB_DIAMETER / 2)
        .extrude(ISOLATOR_KNOB_LENGTH)
        .translate((0, 0, MANIFOLD_BAR_HEIGHT / 2))
    )


# ── Band clamp ───────────────────────────────────────────────────────────────


def make_band():
    """Two rings around each cylinder with a flat connector and M8 rod."""
    wrap_outer = TANK_RADIUS + BAND_THICKNESS
    half_spacing = CYLINDER_SPACING / 2

    left_ring = (
        cq.Workplane("XY")
        .circle(wrap_outer)
        .circle(TANK_RADIUS)
        .extrude(BAND_WIDTH)
        .translate((-half_spacing, 0, 0))
    )

    right_ring = (
        cq.Workplane("XY")
        .circle(wrap_outer)
        .circle(TANK_RADIUS)
        .extrude(BAND_WIDTH)
        .translate((half_spacing, 0, 0))
    )

    flat_connector = (
        cq.Workplane("XY")
        .box(CYLINDER_GAP, BAND_FLAT_WIDTH, BAND_WIDTH)
        .translate((0, 0, BAND_WIDTH / 2))
    )

    rod = (
        cq.Workplane("XY")
        .circle(M8_ROD_DIAMETER / 2)
        .extrude(M8_ROD_PROTRUSION + BAND_FLAT_THICKNESS)
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((0, -BAND_FLAT_WIDTH / 2, BAND_WIDTH / 2))
    )

    return left_ring.union(right_ring).union(flat_connector).union(rod)


# ── Full twinset assembly ────────────────────────────────────────────────────


def make_d12_twinset():
    """Assemble the complete D12 double tank with valves, manifold, and bands.

    Returns
    -------
    cq.Assembly
        Origin at bottom-center of the twinset, tanks standing upright along Z.
    """
    assy = Assembly(name="d12_twinset")

    tank_z_offset = TANK_DOME_HEIGHT
    valve_z = tank_z_offset + TANK_BODY_HEIGHT + TANK_DOME_HEIGHT
    manifold_z = valve_z + VALVE_NECK_HEIGHT + VALVE_BODY_HEIGHT / 2

    half_spacing = CYLINDER_SPACING / 2

    for side, x in [("left", -half_spacing), ("right", half_spacing)]:
        assy.add(
            make_tank_body(),
            name=f"tank_{side}",
            loc=loc(x, 0, tank_z_offset),
            color=COLOR_STEEL,
        )

        assy.add(
            make_post_valve(side),
            name=f"valve_{side}",
            loc=loc(x, 0, valve_z),
            color=COLOR_BLACK,
        )

    assy.add(
        make_manifold_bar(),
        name="manifold_bar",
        loc=loc(0, 0, manifold_z),
        color=COLOR_CHROME,
    )

    assy.add(
        make_isolator_knob(),
        name="isolator_knob",
        loc=loc(0, 0, manifold_z),
        color=COLOR_BLACK,
    )

    for i, z_pos in enumerate(BAND_POSITIONS):
        assy.add(
            make_band(),
            name=f"band_{i}",
            loc=loc(0, 0, z_pos),
            color=COLOR_CHROME,
        )

    return assy
