"""2D orthographic drawing exports for workbench_v2.

Run with:
    uv run python src/workbench/workbench_v2_drawings.py

Outputs SVG files next to this script (one per view).
"""

import sys
from pathlib import Path

import cadquery as cq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workbench.workbench_v2 import make_workbench

OUTPUT_DIR = Path(__file__).parent


def rotated(shape: cq.Shape, axis: tuple, angle: float) -> cq.Shape:
    return shape.rotate((0, 0, 0), axis, angle)


def export_svg(
    shape: cq.Shape,
    name: str,
    width: int = 1600,
    height: int = 1000,
) -> None:
    out = OUTPUT_DIR / f"workbench_v2_{name}.svg"
    cq.exporters.export(
        shape,
        str(out),
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
    print(f"Exported: {out.name}")


def main() -> None:
    workbench = make_workbench(include_props=False)
    compound = workbench.toCompound()

    # Top view (plan) — project down Z axis
    export_svg(compound, "top", width=1800, height=900)

    # Front elevation — rotate -90° around X so we look along Y
    front = rotated(compound, (-1, 0, 0), 90)
    export_svg(front, "front", width=1800, height=900)

    # Side elevation (right side) — front rotation + -90° around Y
    side = rotated(front, (0, -1, 0), 90)
    export_svg(side, "side_right", width=900, height=900)

    # 3D isometric-ish view
    iso = rotated(compound, (-1, 0, 0), 65)
    iso = rotated(iso, (0, 1, 0), -35)
    export_svg(iso, "iso", width=1800, height=1100)


if __name__ == "__main__":
    main()
