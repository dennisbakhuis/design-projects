"""
Colored isometric PNG render of the workbench assembly (with props).
Uses cadquery.vis VTK pipeline directly for correct CadQuery Assembly colors.

Run with:
    DISPLAY=:99 uv run python src/workbench/render_colored.py

Requires Xvfb:
    Xvfb :99 -screen 0 1920x1080x24 &

Output: src/workbench/workbench_iso_colored.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cadquery.vis import (
    toVTKAssy,
    vtkRenderer,
    vtkRenderWindow,
    vtkWindowToImageFilter,
    vtkPNGWriter,
)
from workbench.workbench_v2 import make_workbench

OUTPUT = Path(__file__).parent / "workbench_iso_colored.png"


def render(
    output_path: Path = OUTPUT,
    width: int = 1800,
    height: int = 1000,
    elevation: float = -35,
    azimuth: float = 20,
    roll: float = -15,
) -> None:
    print("Building workbench model (with props)...")
    assy = make_workbench(include_props=True)

    print("Building VTK scene...")
    renderer = vtkRenderer()
    renderer.SetBackground(0.96, 0.96, 0.96)

    for act in toVTKAssy(assy):
        renderer.AddActor(act)

    # Camera: frontal-right, low — shows front face, cart + wheels, tanks
    cam = renderer.GetActiveCamera()
    cam.SetPosition(3000, -5500, 800)
    cam.SetFocalPoint(-300, 0, 500)
    cam.SetViewUp(0, 0, 1)
    renderer.ResetCameraClippingRange()

    win = vtkRenderWindow()
    win.SetSize(width, height)
    win.AddRenderer(renderer)
    win.Render()

    print("Writing PNG...")
    w2i = vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()

    writer = vtkPNGWriter()
    writer.SetFileName(str(output_path))
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()
    print(f"PNG saved: {output_path}")


if __name__ == "__main__":
    render()
