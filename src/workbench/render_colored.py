"""
Colored isometric PNG render of the workbench (with props).

Run with:
    uv run python src/workbench/render_colored.py

Output: src/workbench/workbench_iso_colored.png
Requires: pyvista, xvfb (apt install xvfb)
"""

import sys
from pathlib import Path
import tempfile
import os

import pyvista as pv

pv.start_xvfb()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from workbench.workbench_v2 import make_workbench
import cadquery as cq

OUTPUT = Path(__file__).parent / "workbench_iso_colored.png"


def walk_assy(assy, parts: list) -> None:
    """Recursively collect (shape, rgb_tuple) from assembly tree."""
    for child in assy.children:
        col = (0.72, 0.52, 0.30)  # default wood
        if child.color:
            t = child.color.toTuple()
            col = (t[0], t[1], t[2])
        if child.obj is not None:
            try:
                shape = child.obj.val().moved(child.loc)
                parts.append((shape, col))
            except Exception:
                pass
        walk_assy(child, parts)


def render(output_path: Path = OUTPUT, width: int = 1800, height: int = 1000) -> None:
    print("Building workbench model (with props)...")
    assy = make_workbench(include_props=True)

    print("Collecting parts...")
    parts: list = []
    walk_assy(assy, parts)
    print(f"  {len(parts)} parts found")

    pl = pv.Plotter(off_screen=True, window_size=[width, height])
    pl.background_color = "#f2f2f2"

    print("Adding meshes...")
    for shape, col in parts:
        tmp = tempfile.mktemp(suffix=".stl")
        try:
            cq.exporters.export(shape, tmp)
            mesh = pv.read(tmp)
            if mesh.n_points > 0:
                pl.add_mesh(
                    mesh, color=col, show_edges=False,
                    smooth_shading=True, specular=0.2, specular_power=10,
                )
        except Exception:
            pass
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    pl.camera_position = [(5000, -4000, 4000), (0, 0, 500), (0, 0, 1)]
    pl.screenshot(str(output_path))
    print(f"PNG saved: {output_path}")


if __name__ == "__main__":
    render()
