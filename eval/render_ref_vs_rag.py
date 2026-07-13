"""Render a 1x2 contour figure comparing:
   cavity reference (left) vs cavity RAG-generated (right).

Reads OpenFOAM cases through pyvista, extracts the z-mid slice, and
plots velocity magnitude.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as tri
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
pv.set_plot_theme("document")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "benchmark" / "exec_end_to_end"
OUT_PDF = HERE.parent / "fig_ref_vs_rag.pdf"

CASES = [
    {"col": 0,
     "path": ROOT / "cavity" / "reference_case",
     "title": "Reference",
     "field": "U", "comp": "mag", "cmap": "viridis",
     "label": r"$|U|$ (m/s)"},
    {"col": 1,
     "path": ROOT / "cavity" / "cavity_rag",
     "title": "Agent",
     "field": "U", "comp": "mag", "cmap": "viridis",
     "label": r"$|U|$ (m/s)"},
]


def load(case_dir: Path, field: str, comp: str | None):
    stub = case_dir / "case.foam"
    if not stub.exists():
        stub.touch()
    reader = pv.POpenFOAMReader(str(stub))
    if reader.time_values:
        reader.set_active_time_value(reader.time_values[-1])
    reader.disable_all_patch_arrays()
    reader.enable_patch_array("internalMesh")
    mb = reader.read()
    mesh = next((mb[i] for i in range(mb.n_blocks)
                 if mb[i] is not None and hasattr(mb[i], "n_points")
                 and mb[i].n_points > 0), None)
    if mesh is None:
        return None, None
    if field in mesh.cell_data and field not in mesh.point_data:
        mesh = mesh.cell_data_to_point_data()
    raw = mesh.point_data.get(field)
    if raw is None:
        raw = mesh.cell_data.get(field)
    if raw is None:
        return None, None
    arr = np.asarray(raw)
    if comp == "mag" and arr.ndim == 2 and arr.shape[1] == 3:
        values = np.linalg.norm(arr, axis=1)
    else:
        values = arr if arr.ndim == 1 else arr[:, 0]

    bounds = mesh.bounds
    zmid = 0.5 * (bounds[4] + bounds[5])
    slc = mesh.slice(normal="z", origin=(0, 0, zmid))
    if slc.n_points == 0:
        slc = mesh
    if field in slc.cell_data and field not in slc.point_data:
        slc = slc.cell_data_to_point_data()
    v = slc.point_data.get(field)
    if v is not None:
        arr = np.asarray(v)
        if comp == "mag" and arr.ndim == 2 and arr.shape[1] == 3:
            values = np.linalg.norm(arr, axis=1)
        else:
            values = arr if arr.ndim == 1 else arr[:, 0]
    return np.asarray(slc.points), values


def main():
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.titlesize": 10,
    })

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.0),
                             gridspec_kw=dict(wspace=0.15))

    loaded = []
    vmin, vmax = np.inf, -np.inf
    for spec in CASES:
        pts, vals = load(spec["path"], spec["field"], spec["comp"])
        loaded.append((pts, vals, spec))
        if pts is not None:
            vmin = min(vmin, float(vals.min()))
            vmax = max(vmax, float(vals.max()))

    last_cs = None
    for pts, vals, spec in loaded:
        ax = axes[spec["col"]]
        if pts is None:
            ax.axis("off")
            ax.text(0.5, 0.5, "case not available",
                    transform=ax.transAxes, ha="center", va="center",
                    color="grey")
            continue
        triang = tri.Triangulation(pts[:, 0], pts[:, 1])
        cs = ax.tricontourf(triang, vals, levels=18,
                            cmap=spec["cmap"], vmin=vmin, vmax=vmax)
        ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(spec["title"], fontsize=10)
        last_cs = cs

    # Attach the shared colorbar to both axes so both panels shrink
    # by the same amount, keeping them visually identical in size.
    if last_cs is not None:
        cbar = fig.colorbar(last_cs, ax=list(axes), shrink=0.9,
                            pad=0.02, fraction=0.04)
        cbar.ax.tick_params(labelsize=7)
        cbar.set_label(CASES[0]["label"], fontsize=8)

    fig.savefig(OUT_PDF, bbox_inches="tight", dpi=220)
    plt.close(fig)
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
