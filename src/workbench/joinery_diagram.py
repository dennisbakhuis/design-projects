"""
Joinery diagram: stretcher-to-leg pocket screw connection.
Generates a technical illustration with three views.
"""

import math
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
from matplotlib.patches import Arc, FancyArrowPatch

OUTPUT = Path(__file__).parent

# ── Colour palette ───────────────────────────────────────────────────────────
C_WOOD   = "#D4A96A"   # warm oak
C_EDGE   = "#6B3A2A"   # dark brown outline
C_SCREW  = "#888888"   # screw / steel
C_DIM    = "#333333"   # dimension lines
C_ANNOT  = "#1A1A6E"   # annotation text
C_BG     = "#F8F5EF"   # page background
C_HOLE   = "#B07040"   # pocket hole shading


def dim_arrow(ax, x0, y0, x1, y1, label, offset=(0, 4), fontsize=7, color=C_DIM):
    """Draw a dimension line with arrowheads and a label."""
    ax.annotate(
        "", xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(arrowstyle="<->", color=color, lw=0.8),
    )
    mx, my = (x0 + x1) / 2 + offset[0], (y0 + y1) / 2 + offset[1]
    ax.text(mx, my, label, ha="center", va="bottom", fontsize=fontsize,
            color=color, fontfamily="monospace")


def draw_screw(ax, x, y, angle_deg, length=18, head_r=2.5):
    """Draw a stylised pocket screw at (x,y) pointing in angle_deg direction."""
    rad = math.radians(angle_deg)
    dx, dy = math.cos(rad) * length, math.sin(rad) * length
    # shank
    ax.plot([x, x + dx], [y, y + dy], color=C_SCREW, lw=1.8, zorder=5)
    # head circle
    head = plt.Circle((x, y), head_r, color=C_SCREW, zorder=6)
    ax.add_patch(head)
    # thread lines
    for t in [0.3, 0.55, 0.75]:
        tx, ty = x + dx * t, y + dy * t
        perp = math.radians(angle_deg + 90)
        ax.plot(
            [tx - math.cos(perp) * 2.5, tx + math.cos(perp) * 2.5],
            [ty - math.sin(perp) * 2.5, ty + math.sin(perp) * 2.5],
            color=C_SCREW, lw=0.7, zorder=5,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Figure layout
# ═══════════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(14, 9), facecolor=C_BG)
fig.suptitle(
    "Werkbank v2 — Verbinding dwarsverbinding aan poot  (Pocket-schroef)",
    fontsize=13, fontweight="bold", color=C_EDGE, y=0.97,
)

# Three panels
ax1 = fig.add_axes([0.02, 0.08, 0.30, 0.82], facecolor=C_BG)  # front elevation
ax2 = fig.add_axes([0.36, 0.08, 0.30, 0.82], facecolor=C_BG)  # section (pocket detail)
ax3 = fig.add_axes([0.70, 0.08, 0.28, 0.82], facecolor=C_BG)  # isometric

for ax in (ax1, ax2, ax3):
    ax.set_aspect("equal")
    ax.axis("off")

# ─────────────────────────────────────────────────────────────────────────────
# Panel 1: Front elevation (assembled joint)
# Scale: 1 unit = 1 mm, shown area ~ 280 × 340 mm
# ─────────────────────────────────────────────────────────────────────────────
ax1.set_title("Aanzicht voor — Verbinding geassembleerd",
              fontsize=9, color=C_ANNOT, pad=8)

# Leg (80 × shown 300 mm tall, centred at x=80)
LEG_W, LEG_SHOWN = 80, 280
leg_x, leg_y = 30, 40
leg = mpatches.FancyBboxPatch(
    (leg_x, leg_y), LEG_W, LEG_SHOWN,
    boxstyle="square,pad=0", linewidth=1.2,
    edgecolor=C_EDGE, facecolor=C_WOOD,
)
ax1.add_patch(leg)

# Grain lines on leg
for gy in range(leg_y + 20, leg_y + LEG_SHOWN, 25):
    ax1.plot([leg_x + 8, leg_x + LEG_W - 8], [gy, gy + 4],
             color=C_EDGE, lw=0.4, alpha=0.35)

# Stretcher (52 mm deep × 75 mm tall × 180 mm shown, flush left face of leg)
STR_D, STR_H, STR_L = 52, 75, 180
str_x = leg_x + LEG_W          # abuts leg right face
str_y = leg_y + LEG_SHOWN - 170  # roughly at top-rail height

stretcher = mpatches.FancyBboxPatch(
    (str_x, str_y), STR_L, STR_H,
    boxstyle="square,pad=0", linewidth=1.2,
    edgecolor=C_EDGE, facecolor=C_WOOD,
)
ax1.add_patch(stretcher)

# Grain lines on stretcher
for gx in range(str_x + 15, str_x + STR_L, 20):
    ax1.plot([gx, gx + 5], [str_y + 10, str_y + STR_H - 10],
             color=C_EDGE, lw=0.4, alpha=0.35)

# Pocket screw symbols (viewed from front — circles at screw positions)
for sy_off in [18, 52]:
    sc = plt.Circle((str_x + 22, str_y + sy_off), 4,
                    color=C_SCREW, zorder=6, linewidth=1)
    ax1.add_patch(sc)
    ax1.plot(str_x + 22, str_y + sy_off, "x", color="white",
             markersize=4, markeredgewidth=1.2, zorder=7)

# Dimension: leg width
dim_arrow(ax1, leg_x, leg_y - 18, leg_x + LEG_W, leg_y - 18,
          "80 mm", offset=(0, -5))
# Dimension: stretcher height
dim_arrow(ax1, str_x + STR_L + 12, str_y, str_x + STR_L + 12, str_y + STR_H,
          "75 mm", offset=(4, 0))
# Dimension: stretcher depth (into page — label only)
ax1.text(str_x + STR_L / 2, str_y - 14,
         "diepte 52 mm (zie doorsnede →)", ha="center", fontsize=7,
         color=C_ANNOT, style="italic")

# Labels
ax1.text(leg_x + LEG_W / 2, leg_y + LEG_SHOWN + 10, "Poot\n80×80 mm",
         ha="center", fontsize=8, color=C_ANNOT, fontweight="bold")
ax1.text(str_x + STR_L / 2, str_y + STR_H + 10, "Dwarsverbinding\n52×75 mm",
         ha="center", fontsize=8, color=C_ANNOT, fontweight="bold")

# Screw label
ax1.annotate("2× pocket-schroef\n50 mm (Ø 4 mm)",
             xy=(str_x + 22, str_y + 35),
             xytext=(str_x + 80, str_y + 20),
             fontsize=7.5, color=C_SCREW,
             arrowprops=dict(arrowstyle="->", color=C_SCREW, lw=0.8))

ax1.set_xlim(0, 310)
ax1.set_ylim(10, 380)

# ─────────────────────────────────────────────────────────────────────────────
# Panel 2: Section through the pocket screw (side view, looking along leg)
# Shows the angled pocket hole drilled through the stretcher end
# ─────────────────────────────────────────────────────────────────────────────
ax2.set_title("Doorsnede zijkant — Pocket-schroef detail",
              fontsize=9, color=C_ANNOT, pad=8)

# Leg cross-section (80 × 80 mm square, centred)
lc_x, lc_y = 60, 130
ax2.add_patch(mpatches.FancyBboxPatch(
    (lc_x, lc_y), 80, 200, boxstyle="square,pad=0",
    linewidth=1.2, edgecolor=C_EDGE, facecolor=C_WOOD,
))
for gy in range(lc_y + 15, lc_y + 200, 22):
    ax2.plot([lc_x + 6, lc_x + 74], [gy, gy + 3],
             color=C_EDGE, lw=0.4, alpha=0.35)

# Stretcher end (52 mm deep × 75 mm tall, abutting leg)
sc_x, sc_y = lc_x + 80, lc_y + 60
ax2.add_patch(mpatches.FancyBboxPatch(
    (sc_x, sc_y), 52, 75, boxstyle="square,pad=0",
    linewidth=1.2, edgecolor=C_EDGE, facecolor=C_WOOD,
))
# End grain texture
for gx in range(sc_x + 6, sc_x + 52, 8):
    ax2.plot([gx, gx + 3], [sc_y + 5, sc_y + 70],
             color=C_EDGE, lw=0.35, alpha=0.4)

# Pocket hole: angled channel at ~15° from horizontal in the stretcher
ANGLE = 15   # degrees below horizontal
rad = math.radians(ANGLE)
# Entry point of pocket hole (on the back face of the stretcher, ~15mm from leg)
ph_entry_x = sc_x + 48   # near the leg-end face
ph_entry_y = sc_y + 14   # near bottom of stretcher

# Hole direction: toward the leg face, angled downward
# The drill enters from the bottom face of the stretcher
hole_len = 38
ph_exit_x = ph_entry_x - hole_len * math.cos(rad)
ph_exit_y = ph_entry_y + hole_len * math.sin(rad)

# Draw pocket channel (shaded)
hole_w = 7
perp = math.radians(ANGLE + 90)
pts = [
    (ph_entry_x + math.cos(perp) * hole_w / 2,
     ph_entry_y + math.sin(perp) * hole_w / 2),
    (ph_exit_x + math.cos(perp) * hole_w / 2,
     ph_exit_y + math.sin(perp) * hole_w / 2),
    (ph_exit_x - math.cos(perp) * hole_w / 2,
     ph_exit_y - math.sin(perp) * hole_w / 2),
    (ph_entry_x - math.cos(perp) * hole_w / 2,
     ph_entry_y - math.sin(perp) * hole_w / 2),
]
hole_poly = plt.Polygon(pts, closed=True, facecolor=C_HOLE,
                        edgecolor=C_EDGE, lw=0.8, zorder=4, alpha=0.7)
ax2.add_patch(hole_poly)

# Screw in hole
draw_screw(ax2, ph_entry_x - 4, ph_entry_y + 2,
           180 - ANGLE, length=36, head_r=4)

# Angle arc + label
arc_r = 18
arc = Arc((ph_entry_x, ph_entry_y), arc_r * 2, arc_r * 2,
          angle=0, theta1=180 - ANGLE, theta2=180,
          color=C_DIM, lw=0.8)
ax2.add_patch(arc)
ax2.text(ph_entry_x - arc_r - 14, ph_entry_y + 6, f"{ANGLE}°",
         fontsize=7, color=C_DIM, ha="center")

# Labels
ax2.text(lc_x + 40, lc_y + 210, "Poot 80×80 mm\n(zijaanzicht)",
         ha="center", fontsize=8, color=C_ANNOT, fontweight="bold")
ax2.text(sc_x + 26, sc_y + 85, "Einde\ndwarsverb.",
         ha="center", fontsize=7.5, color=C_ANNOT)

# Pocket hole annotation
ax2.annotate(
    "Pocket-gat\n(Kreg-jig, 15°)",
    xy=((ph_entry_x + ph_exit_x) / 2 + 4,
        (ph_entry_y + ph_exit_y) / 2),
    xytext=(sc_x + 75, sc_y + 55),
    fontsize=7.5, color=C_ANNOT,
    arrowprops=dict(arrowstyle="->", color=C_ANNOT, lw=0.8),
)

# Glue face annotation
ax2.annotate(
    "Lijmvlak\n(houtlijm D3)",
    xy=(sc_x, sc_y + 37),
    xytext=(sc_x - 55, sc_y + 75),
    fontsize=7.5, color="#2A6A2A",
    arrowprops=dict(arrowstyle="->", color="#2A6A2A", lw=0.8),
)
# Glue line
ax2.plot([sc_x, sc_x], [sc_y, sc_y + 75],
         color="#2A6A2A", lw=2.5, alpha=0.4, zorder=3)

# Dimension: pocket hole entry from bottom
dim_arrow(ax2, sc_x + 55, sc_y, sc_x + 55, ph_entry_y,
          "14 mm", offset=(5, 0), fontsize=6.5)

ax2.set_xlim(10, 220)
ax2.set_ylim(90, 370)

# ─────────────────────────────────────────────────────────────────────────────
# Panel 3: Isometric sketch (oblique projection)
# ─────────────────────────────────────────────────────────────────────────────
ax3.set_title("Isometrisch — Hoekverbinding",
              fontsize=9, color=C_ANNOT, pad=8)

def iso(x, y, z, sx=0.5, sy=0.4):
    """Simple oblique projection."""
    return x + z * sx, y + z * sy

# Leg: 80×80 base, 240 tall — shown as 3D box
lw, ld, lh = 80, 80, 240
lo = (40, 60)  # origin

def leg_box(ax, ox, oy, w, d, h, alpha=1.0):
    # front face
    ax.add_patch(plt.Polygon(
        [iso(ox, oy, 0), iso(ox + w, oy, 0),
         iso(ox + w, oy + h, 0), iso(ox, oy + h, 0)],
        closed=True, facecolor=C_WOOD, edgecolor=C_EDGE,
        lw=1.0, alpha=alpha,
    ))
    # top face
    ax.add_patch(plt.Polygon(
        [iso(ox, oy + h, 0), iso(ox + w, oy + h, 0),
         iso(ox + w, oy + h, d), iso(ox, oy + h, d)],
        closed=True, facecolor="#C49050", edgecolor=C_EDGE,
        lw=1.0, alpha=alpha,
    ))
    # right face
    ax.add_patch(plt.Polygon(
        [iso(ox + w, oy, 0), iso(ox + w, oy, d),
         iso(ox + w, oy + h, d), iso(ox + w, oy + h, 0)],
        closed=True, facecolor="#BA8040", edgecolor=C_EDGE,
        lw=1.0, alpha=alpha,
    ))

leg_box(ax3, lo[0], lo[1], lw, ld, lh)

# Stretcher: 52 deep × 75 tall × 180 long, attaches to right face of leg at top
sw, sh, sl = 52, 75, 180
sy_off = lh - sh - 20   # distance from bottom of leg
str_ox = lo[0] + lw     # starts at right face of leg
str_oy = lo[1] + sy_off

# stretcher front face (normal to X, so we draw it with depth in Z)
ax3.add_patch(plt.Polygon(
    [iso(str_ox, str_oy, 0),
     iso(str_ox, str_oy, sw),
     iso(str_ox, str_oy + sh, sw),
     iso(str_ox, str_oy + sh, 0)],
    closed=True, facecolor="#BA8040", edgecolor=C_EDGE, lw=1.0,
))
# stretcher top face
ax3.add_patch(plt.Polygon(
    [iso(str_ox, str_oy + sh, 0),
     iso(str_ox, str_oy + sh, sw),
     iso(str_ox + sl, str_oy + sh, sw),
     iso(str_ox + sl, str_oy + sh, 0)],
    closed=True, facecolor="#C49050", edgecolor=C_EDGE, lw=1.0,
))
# stretcher outer face (visible long face, y direction)
ax3.add_patch(plt.Polygon(
    [iso(str_ox, str_oy, sw),
     iso(str_ox + sl, str_oy, sw),
     iso(str_ox + sl, str_oy + sh, sw),
     iso(str_ox, str_oy + sh, sw)],
    closed=True, facecolor=C_WOOD, edgecolor=C_EDGE, lw=1.0,
))

# Screw symbols (2 dots on the leg face)
for s_z in [12, 42]:
    sx_, sy_ = iso(str_ox, str_oy + s_z + 12, 0)
    ax3.plot(sx_, sy_, "o", color=C_SCREW, markersize=5, zorder=7)

# Labels
lx, ly = iso(lo[0] + lw / 2, lo[1] + lh + 8, ld / 2)
ax3.text(lx, ly, "Poot 80×80", ha="center", fontsize=7.5,
         color=C_ANNOT, fontweight="bold")

slx, sly = iso(str_ox + sl / 2, str_oy - 14, sw / 2)
ax3.text(slx, sly, "Dwarsverbinding 52×75", ha="center",
         fontsize=7.5, color=C_ANNOT, fontweight="bold")

# Screw annotation
sc_iso = iso(str_ox, str_oy + 24, 0)
ax3.annotate("Pocket-schroeven\n2× per verbinding",
             xy=sc_iso,
             xytext=(sc_iso[0] - 55, sc_iso[1] - 30),
             fontsize=7, color=C_SCREW,
             arrowprops=dict(arrowstyle="->", color=C_SCREW, lw=0.8))

ax3.set_xlim(-10, 310)
ax3.set_ylim(20, 380)

# ─────────────────────────────────────────────────────────────────────────────
# Footer note
# ─────────────────────────────────────────────────────────────────────────────
fig.text(
    0.5, 0.02,
    "Verbindingsmethode: pocket-schroef (Kreg-jig of equivalent) · 2 schroeven per verbindingspunt · "
    "lijmvlak aanbrengen vóór aanschroeven · schroeflengte 50 mm",
    ha="center", fontsize=7.5, color=C_DIM, style="italic",
)

out = OUTPUT / "joinery_stretcher_to_leg.png"
fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=C_BG)
print(f"Saved: {out}")
