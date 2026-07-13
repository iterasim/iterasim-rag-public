"""Regenerate every figure in the IteraSim RAG manuscript.

Each figure lives in a stand-alone function so it can be tuned or
regenerated in isolation. All font sizes, figure dimensions, colours
and output paths are configurable through the CONFIG dict at the top
of this file.

Figures produced:
    fig_retrieval_per_category.pdf   -- bar chart of per-category retrieval score
    fig_retrieval_heatmap.pdf        -- per-case coverage heatmap
    fig_latency.pdf                  -- retrieval-latency CDF
    fig_executability.pdf            -- per-case executability + category means
    fig_cfd_results.pdf              -- composite of 6 CFD field renders (pyvista)
    fig_contour_comparison.pdf       -- Category-C reference vs agent-patched pairs
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import mean

# =====================================================================
#  CONFIG -- edit these knobs to change appearance across all figures.
# =====================================================================
HERE = Path(__file__).resolve().parent

CONFIG: dict = {
    # ---- I/O ----
    # Users can override these via environment variables:
    #   ITERASIM_QUERIES_JSON, ITERASIM_RESULTS_ROOT, ITERASIM_RUNS_ROOT
    "output_dir":       HERE,
    "eval_queries":     Path(os.environ.get(
        "ITERASIM_QUERIES_JSON",
        str(HERE.parent / "benchmark" / "benchmark_queries.json"),
    )),
    "eval_results_root": Path(os.environ.get(
        "ITERASIM_RESULTS_ROOT",
        str(HERE.parent / "results"),
    )),
    # If your local results/ folder has a single subrun you want
    # pinned, name it here.  Set to None (default) to auto-pick the
    # newest timestamp under eval_results_root.
    "eval_results_pin": None,
    "runs_root":        Path(os.environ.get(
        "ITERASIM_RUNS_ROOT",
        str(HERE.parent / "runs"),
    )),

    # ---- Global matplotlib settings (Journal Standard) ----
    "font_family":      "serif",
    "font_size":        9,
    "title_size":       10,
    "label_size":       9,
    "tick_size":        8,
    "dpi":              300,
    "use_tex":          False,

    # ---- Category colour palette (used across figures) ----
    "cat_colours": {"A": "#1f77b4",
                    "B": "#2ca02c",
                    "C": "#ff7f0e",
                    "D": "#d62728"},
    "cat_label":   {"A": "Zero-shot",
                    "B": "Few-shot",
                    "C": "Alt. conditions",
                    "D": "Turbulence switch"},

    # ---- Per-figure geometry ----
    "fig_per_category":  {"size": (4.8, 3.2)},
    "fig_heatmap":       {"size": (7.0, 2.2)},
    "fig_latency":       {"size": (4.0, 2.8)},
    "fig_executability": {"size": (10.0, 3.2)},
    "fig_cfd_results":   {"size": (8.5, 5.2)},
    "fig_contour":       {"size": (9.5, 9.5)},

    # ---- Executability scores (per-case 0-4) ----
    "executability": {
        "A1": 3, "A2": 3, "A3": 4, "A4": 4, "A5": 3, "A6": 3,
        "B1": 3, "B2": 4, "B3": 3, "B4": 4,
        "C1": 3, "C2": 3, "C3": 3, "C4": 4, "C5": 4,
        "C6": 4, "C7": 4, "C8": 3, "C9": 3, "C10": 3,
        "D1": 3, "D2": 3, "D3": 3, "D4": 3, "D5": 3,
        "D6": 3, "D7": 4, "D8": 3,
    },
}


# =====================================================================
#  Helpers
# =====================================================================
def _apply_style() -> None:
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family":      CONFIG["font_family"],
        "font.size":        CONFIG["font_size"],
        "axes.titlesize":   CONFIG["title_size"],
        "axes.labelsize":   CONFIG["label_size"],
        "xtick.labelsize":  CONFIG["tick_size"],
        "ytick.labelsize":  CONFIG["tick_size"],
        "text.usetex":      CONFIG["use_tex"],
        "savefig.dpi":      CONFIG["dpi"],
        "axes.linewidth":   0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
    })


def _latest_eval() -> dict:
    root = CONFIG["eval_results_root"]
    if not root.exists():
        sys.exit(f"Evaluation results root directory does not exist: {root}")
    pin = CONFIG.get("eval_results_pin")
    if pin:
        pinned = root / pin
        if pinned.exists():
            return json.loads((pinned / "results.json").read_text())
        print(f"[warn] pinned run {pin} not found; falling back to newest")
    runs = sorted(p for p in root.iterdir()
                  if p.is_dir() and p.name.startswith("2026"))
    if not runs:
        sys.exit(f"No eval-result directory found matching '2026*' under {root}")
    return json.loads((runs[-1] / "results.json").read_text())


def _load_retrieval() -> list[dict]:
    """Return per-case retrieval records enriched with case_id/category."""
    payload = _latest_eval()
    if not CONFIG["eval_queries"].exists():
        sys.exit(f"Benchmark queries file missing: {CONFIG['eval_queries']}")
    queries = json.loads(CONFIG["eval_queries"].read_text())
    out = []
    for r in payload["retrieval"]:
        q = queries[r["idx"] - 1]
        out.append({**r,
                    "case_id":  q["case_id"],
                    "category": q["category"],
                    "title":    q["title"]})
    return out


def _out(name: str) -> Path:
    return CONFIG["output_dir"] / name


# =====================================================================
#  Figure 1: per-category retrieval coverage
# =====================================================================
def fig_retrieval_per_category() -> Path:
    import matplotlib.pyplot as plt
    import numpy as np

    records = _load_retrieval()
    cats = ["A", "B", "C", "D"]
    by_cat = {c: [r["score_pct"] for r in records if r["category"] == c] for c in cats}

    fig, ax = plt.subplots(figsize=CONFIG["fig_per_category"]["size"])
    xs = np.arange(len(cats))
    means = [np.mean(by_cat[c]) for c in cats]
    stds = [np.std(by_cat[c], ddof=1) if len(by_cat[c]) > 1 else 0.0 for c in cats]
    
    # Clean, professional thin errorbars
    ax.bar(xs, means, yerr=stds, capsize=3,
           error_kw=dict(elinewidth=0.8, ecolor="#333333"),
           color=[CONFIG["cat_colours"][c] for c in cats],
           edgecolor="#222222", linewidth=0.7, alpha=0.85, width=0.55)

    rng = np.random.default_rng(42)
    for i, c in enumerate(cats):
        vals = by_cat[c]
        jitter = rng.uniform(-0.12, 0.12, size=len(vals))
        ax.scatter(np.full(len(vals), i) + jitter, vals,
                   s=16, color="#111111", edgecolor="none", alpha=0.6, zorder=3)

    all_vals = [v for c in cats for v in by_cat[c]]
    overall_mean = float(np.mean(all_vals))
    overall_median = float(np.median(all_vals))
    ax.axhline(overall_mean, color="#555555", linestyle="--",
               linewidth=0.8,
               label=f"Overall mean ({overall_mean:.1f}%)")
    ax.axhline(overall_median, color="#111111", linestyle=":",
               linewidth=0.8,
               label=f"Overall median ({overall_median:.1f}%)")

    ax.set_xticks(xs)
    ax.set_xticklabels(cats)
    ax.set_ylabel("Retrieval score (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Per-Category Retrieval Coverage", pad=10)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    fig.tight_layout()
    out = _out("fig_retrieval_per_category.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {out}")
    return out


# =====================================================================
#  Figure 2: per-case retrieval heatmap
# =====================================================================
def fig_retrieval_heatmap() -> Path:
    import matplotlib.pyplot as plt
    import numpy as np

    records = _load_retrieval()
    cats = ["A", "B", "C", "D"]
    grouped = {c: sorted([r for r in records if r["category"] == c],
                         key=lambda x: int(x["case_id"][1:]))
               for c in cats}
    max_n = max(len(grouped[c]) for c in cats)

    grid = np.full((len(cats), max_n), np.nan)
    labels = np.full((len(cats), max_n), "", dtype=object)
    for i, c in enumerate(cats):
        for j, r in enumerate(grouped[c]):
            grid[i, j] = r["score_pct"]
            labels[i, j] = r["case_id"]

    fig, ax = plt.subplots(figsize=CONFIG["fig_heatmap"]["size"])
    # Standard linear scientific colormap
    im = ax.imshow(grid, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            if np.isnan(grid[i, j]):
                continue
            txt_c = "black" if grid[i, j] > 45 else "white"
            ax.text(j, i, f"{labels[i, j]}\n{grid[i, j]:.0f}%",
                    ha="center", va="center",
                    fontsize=CONFIG["tick_size"] - 1, color=txt_c)
                    
    ax.set_yticks(np.arange(len(cats)))
    ax.set_yticklabels(cats)
    ax.set_xticks([])
    ax.set_title("Per-Case Retrieval Coverage Matrix", pad=10)
    
    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.03)
    cbar.set_label("Coverage (%)", fontsize=CONFIG["label_size"])
    cbar.ax.tick_params(labelsize=CONFIG["tick_size"])
    cbar.outline.set_linewidth(0.5)
    
    fig.tight_layout()
    out = _out("fig_retrieval_heatmap.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {out}")
    return out


# =====================================================================
#  Figure 3: retrieval-latency CDF
# =====================================================================
def fig_latency() -> Path:
    import matplotlib.pyplot as plt
    import numpy as np

    records = _load_retrieval()
    lats = np.sort([r["retrieval_seconds"] for r in records])
    cdf = np.arange(1, len(lats) + 1) / len(lats)

    DARK_BLUE = "#08306b"

    fig, ax = plt.subplots(figsize=CONFIG["fig_latency"]["size"])
    ax.step(lats, cdf, where="post", color=DARK_BLUE, linewidth=1.6)

    # Modern horizontal clean fill step-under
    ax.fill_between(lats, 0, cdf, step="post", color=DARK_BLUE, alpha=0.10)

    ax.set_xlabel("End-to-end retrieval latency (s)")
    ax.set_ylabel("Cumulative fraction of cases")

    p50 = float(np.median(lats))
    p95 = float(np.percentile(lats, 95))

    ax.axvline(p50, color="#777777", linestyle=":", linewidth=0.8)
    ax.axvline(p95, color="#777777", linestyle=":", linewidth=0.8)

    # Legible callouts: dark-blue bold text on a white patch so the
    # labels stay readable at the reduced two-column figure size.
    label_bbox = dict(boxstyle="round,pad=0.2", facecolor="white",
                      edgecolor="none", alpha=0.85)
    ax.annotate(f"$p_{{50}}$ = {p50:.2f}s", xy=(p50, 0.5),
                xytext=(p50 - 0.85, 0.30),
                fontsize=9, fontweight="bold", color=DARK_BLUE,
                bbox=label_bbox,
                arrowprops=dict(arrowstyle="->", color=DARK_BLUE, lw=0.7))

    ax.annotate(f"$p_{{95}}$ = {p95:.2f}s", xy=(p95, 0.95),
                xytext=(p95 - 0.90, 0.66),
                fontsize=9, fontweight="bold", color=DARK_BLUE,
                bbox=label_bbox,
                arrowprops=dict(arrowstyle="->", color=DARK_BLUE, lw=0.7))

    ax.set_xlim(left=0)
    ax.set_ylim(0, 1.02)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    fig.tight_layout()
    out = _out("fig_latency.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {out}")
    return out


# =====================================================================
#  Figure 4: per-case executability + category means (2-panel)
# =====================================================================
def fig_executability() -> Path:
    import matplotlib.pyplot as plt
    import numpy as np

    scores = CONFIG["executability"]
    cats = ["A", "B", "C", "D"]

    ordered = sorted(scores.keys(), key=lambda k: (k[0], int(k[1:])))
    xs = np.arange(len(ordered))
    ys = [scores[k] for k in ordered]
    colours = [CONFIG["cat_colours"][k[0]] for k in ordered]

    fig, (ax_l, ax_r) = plt.subplots(
        1, 2, figsize=CONFIG["fig_executability"]["size"],
        gridspec_kw={"width_ratios": [3.6, 1.0]}
    )

    # --- Left Panel: Per-Case Executability ---
    ax_l.bar(xs, ys, color=colours, edgecolor="#222222", linewidth=0.5, alpha=0.85, width=0.7)
    ax_l.axhline(3, color="#666666", linestyle="--", linewidth=0.8)
    ax_l.text(len(ordered) - 0.5, 3.08, r"Runnable threshold ($\geq$ 3)",
              ha="right", va="bottom", fontsize=8, color="#555555")

    # Accurate spatial context lines separating families
    boundaries = {"B": 6, "C": 10, "D": 20}
    for x in boundaries.values():
        ax_l.axvline(x - 0.5, color="#dddddd", linewidth=0.7, linestyle="-")

    ax_l.set_xticks(xs)
    ax_l.set_xticklabels(ordered, rotation=90, fontsize=CONFIG["tick_size"])
    ax_l.set_ylabel("Executability Score (0--4)")
    ax_l.set_ylim(0, 4.3)
    ax_l.set_title("Per-Case Executability Verification", pad=10)
    
    handles = [plt.Rectangle((0, 0), 1, 1, color=CONFIG["cat_colours"][c],
                             label=f"{c}: {CONFIG['cat_label'][c]}") for c in cats]
    ax_l.legend(handles=handles, loc="lower right", fontsize=8, frameon=False, ncols=2)
    ax_l.spines["top"].set_visible(False)
    ax_l.spines["right"].set_visible(False)

    # --- Right Panel: Category Means ---
    means = [mean([scores[k] for k in ordered if k[0] == c]) for c in cats]
    totals = {c: sum(scores[k] for k in ordered if k[0] == c) for c in cats}
    counts = {c: 4 * sum(1 for k in ordered if k[0] == c) for c in cats}
    
    ax_r.bar(cats, means, color=[CONFIG["cat_colours"][c] for c in cats],
             edgecolor="#222222", linewidth=0.5, alpha=0.85, width=0.55)
             
    for i, c in enumerate(cats):
        ax_r.text(i, means[i] + 0.08, f"{totals[c]}/{counts[c]}", ha="center", fontsize=7.5)
        
    overall = sum(ys) / len(ys)
    ax_r.axhline(overall, color="#666666", linestyle=":", linewidth=0.8)
    ax_r.text(3.4, overall - 0.15, f"Mean = {overall:.2f}", ha="right", fontsize=7.5, color="#555555")
    
    ax_r.set_ylabel("Mean Score")
    ax_r.set_ylim(0, 4.3)
    ax_r.set_title("Category Means", pad=10)
    ax_r.spines["top"].set_visible(False)
    ax_r.spines["right"].set_visible(False)

    fig.tight_layout()
    out = _out("fig_executability.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {out}")
    return out


# =====================================================================
#  Figure 5: composite CFD field renders (pyvista)
# =====================================================================
def fig_cfd_results() -> Path:
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import numpy as np
    import pyvista as pv
    from matplotlib import cm

    pv.OFF_SCREEN = True
    pv.set_plot_theme("document")

    cases = [
        ("cavity",         "Cavity flow",     "U",           "mag", "viridis", False, "xy"),
        ("pitzDaily",      "PitzDaily",       "U",           "mag", "viridis", False, "xy"),
        ("hotRoom",        "Hot room",        "U",           "mag", "viridis", False, "xy"),
        ("damBreak",       "Dam break",       "alpha.water", None,  "Blues",   False, "xy"),
        ("particleColumn", "Particle column", "U.air",       "mag", "viridis", False, "iso"),
        ("mixerVessel",    "Mixer vessel",    "U",           "mag", "viridis", False, "xy"),
    ]

    def render_one(spec):
        name, title, field, comp, cmap, log_scale, view = spec
        case_dir = CONFIG["runs_root"] / name
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
                     if mb[i] is not None
                     and hasattr(mb[i], "n_points")
                     and mb[i].n_points > 0), None)
        if mesh is None:
            raise RuntimeError(f"No mesh block populated in {case_dir}")
        if field in mesh.cell_data and field not in mesh.point_data:
            mesh = mesh.cell_data_to_point_data()
        raw = mesh.point_data.get(field)
        if raw is None:
            raw = mesh.cell_data.get(field)
        arr = np.asarray(raw)
        if comp == "mag" and arr.ndim == 2 and arr.shape[1] == 3:
            values = np.linalg.norm(arr, axis=1)
        else:
            values = arr if arr.ndim == 1 else arr[:, 0]
        mesh.point_data["display_field"] = values

        bounds = mesh.bounds
        if view == "xy" and name != "particleColumn":
            zmid = 0.5 * (bounds[4] + bounds[5])
            render_mesh = mesh.slice(normal="z", origin=(0, 0, zmid))
            if render_mesh.n_points == 0:
                render_mesh = mesh
        else:
            render_mesh = mesh

        plotter = pv.Plotter(off_screen=True, window_size=(1200, 900))
        plotter.add_mesh(render_mesh, scalars="display_field",
                         cmap=cmap, log_scale=log_scale,
                         show_edges=False, lighting=False,
                         show_scalar_bar=False)
        if view == "xy":
            plotter.view_xy()
        else:
            plotter.view_isometric()
            plotter.camera.zoom(1.3)
        plotter.background_color = "white"
        png = case_dir.parent / "_panels" / f"{name}.png"
        png.parent.mkdir(parents=True, exist_ok=True)
        plotter.screenshot(str(png), transparent_background=True)
        plotter.close()
        return dict(png=png, title=title, cmap=cmap,
                    vmin=float(values.min()),
                    vmax=float(values.max()),
                    bar_label=_bar_label(field, comp))

    records = []
    for spec in cases:
        try:
            records.append(render_one(spec))
        except Exception as e:
            print(f"  [!] {spec[0]} frame extraction skipped: {e}")

    fig, axes = plt.subplots(2, 3, figsize=CONFIG["fig_cfd_results"]["size"],
                             gridspec_kw=dict(wspace=0.18, hspace=0.22))
                             
    for ax, rec, lab in zip(axes.flat, records, "abcdef"):
        img = mpimg.imread(str(rec["png"]))
        ax.imshow(img)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
            
        ax.set_title(f"({lab}) {rec['title']}", loc="left", fontsize=9)
        norm = mcolors.Normalize(vmin=rec["vmin"], vmax=rec["vmax"])
        sm = cm.ScalarMappable(norm=norm, cmap=plt.get_cmap(rec["cmap"]))
        sm.set_array([])
        
        # Clean precise side colorbars
        cbar = fig.colorbar(sm, ax=ax, shrink=0.72, pad=0.03, fraction=0.04)
        cbar.ax.tick_params(labelsize=7)
        cbar.set_label(rec["bar_label"], fontsize=8)
        cbar.outline.set_linewidth(0.5)

    out = _out("fig_cfd_results.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {out}")
    return out


def _bar_label(field: str, comp: str | None) -> str:
    if field == "U" and comp == "mag":
        return r"$|U|$ (m/s)"
    if field == "U.air" and comp == "mag":
        return r"$|U_{\mathrm{air}}|$ (m/s)"
    if field == "T":
        return r"$T$ (K)"
    if field == "alpha.water":
        return r"$\alpha_{\mathrm{water}}$"
    return field


# =====================================================================
#  Figure 6: Category-C contour comparison (reference vs agent-patched)
# =====================================================================
def fig_contour_comparison() -> Path:
    import matplotlib.pyplot as plt
    import matplotlib.tri as tri
    import numpy as np
    import pyvista as pv

    pv.OFF_SCREEN = True
    pv.set_plot_theme("document")

    CASE_PAIRS = [
        {
            "row_label": "Cavity",
            "reference": {"dir": CONFIG["runs_root"] / "cavity",
                          "title": r"Cavity: $U_{\mathrm{lid}} = 1$ m/s (Reference)"},
            "agent":     {"dir": CONFIG["runs_root"] / "cavity_agent_U5",
                          "title": r"Cavity: $U_{\mathrm{lid}} = 5$ m/s (Agent-Patched)"},
            "field":  "U",
            "comp":   "mag",
            "cmap":   "viridis",
            "label":  r"$|U|$ (m/s)",
        },
        {
            "row_label": "Hot room",
            "reference": {"dir": CONFIG["runs_root"] / "hotRoom",
                          "title": r"hotRoom: $T_{\mathrm{floor}} = 320\,$K (Reference)"},
            "agent":     {"dir": CONFIG["runs_root"] / "hotRoom_agent_350_280",
                          "title": r"hotRoom: $T_{\mathrm{floor}} = 350\,$K (Agent-Patched)"},
            "field":  "T",
            "comp":   None,
            "cmap":   "RdBu_r",
            "label":  r"$T$ (K)",
        },
        {
            "row_label": "Dam break",
            "reference": {"dir": CONFIG["runs_root"] / "damBreak",
                          "title": r"damBreak: Column Left (Reference)"},
            "agent":     {"dir": CONFIG["runs_root"] / "damBreak_agent_right",
                          "title": r"damBreak: Column Right (Agent-Patched)"},
            "field":  "alpha.water",
            "comp":   None,
            "cmap":   "Blues",
            "label":  r"$\alpha_{\mathrm{water}}$",
        },
    ]

    def load_slice(case_dir: Path, field: str, comp: str | None):
        stub = case_dir / "case.foam"
        if not case_dir.exists():
            return None
        if not stub.exists():
            stub.touch()
        reader = pv.POpenFOAMReader(str(stub))
        if reader.time_values:
            reader.set_active_time_value(reader.time_values[-1])
        reader.disable_all_patch_arrays()
        reader.enable_patch_array("internalMesh")
        mb = reader.read()
        mesh = next((mb[i] for i in range(mb.n_blocks)
                     if mb[i] is not None
                     and hasattr(mb[i], "n_points")
                     and mb[i].n_points > 0), None)
        if mesh is None:
            return None
        if field in mesh.cell_data and field not in mesh.point_data:
            mesh = mesh.cell_data_to_point_data()
        raw = mesh.point_data.get(field)
        if raw is None:
            raw = mesh.cell_data.get(field)
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
        pts = np.asarray(slc.points)
        if field in slc.cell_data and field not in slc.point_data:
            slc = slc.cell_data_to_point_data()
        v = slc.point_data.get(field)
        if v is not None:
            arr = np.asarray(v)
            if comp == "mag" and arr.ndim == 2 and arr.shape[1] == 3:
                values = np.linalg.norm(arr, axis=1)
            else:
                values = arr if arr.ndim == 1 else arr[:, 0]
        else:
            values = None
        return pts, values

    row_data = []
    for spec in CASE_PAIRS:
        ref = load_slice(spec["reference"]["dir"], spec["field"], spec["comp"])
        agt = load_slice(spec["agent"]["dir"],     spec["field"], spec["comp"])
        ok = (ref is not None and agt is not None and ref[1] is not None and agt[1] is not None)
        row_data.append((ref, agt, ok, spec))

    n_ok = sum(1 for _, _, ok, _ in row_data if ok)
    if n_ok == 0:
        out = _out("fig_contour_comparison.pdf")
        print(f"  [!] No target case data pairs recovered; skipping output matrix to {out}")
        return out

    fig, axes = plt.subplots(len(CASE_PAIRS), 2,
                             figsize=CONFIG["fig_contour"]["size"],
                             gridspec_kw=dict(wspace=0.08, hspace=0.22))
                             
    for row, (ref, agt, ok, spec) in enumerate(row_data):
        if not ok:
            for col in range(2):
                axes[row, col].axis("off")
                axes[row, col].text(0.5, 0.5, "Case sequence data missing\n(Check CASE_PAIRS configuration)",
                                    ha="center", va="center", transform=axes[row, col].transAxes,
                                    fontsize=8, color="grey")
            print(f"  [!] Matrix row validation tracking failed for '{spec['row_label']}'")
            continue
            
        vmin = min(ref[1].min(), agt[1].min())
        vmax = max(ref[1].max(), agt[1].max())
        
        for col, (pts_vals, sub) in enumerate([(ref, spec["reference"]), (agt, spec["agent"])]):
            pts, values = pts_vals
            ax = axes[row, col]
            triang = tri.Triangulation(pts[:, 0], pts[:, 1])
            
            # 15 structured standard levels for continuous visualization
            cs = ax.tricontourf(triang, values, levels=15, cmap=spec["cmap"], vmin=vmin, vmax=vmax)
            ax.set_aspect("equal")
            ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(sub["title"], fontsize=8.5, pad=6)
            
            if col == 1:
                cbar = fig.colorbar(cs, ax=ax, shrink=0.82, pad=0.03, fraction=0.04)
                cbar.ax.tick_params(labelsize=7)
                cbar.set_label(spec["label"], fontsize=8)
                cbar.outline.set_linewidth(0.5)
                
    out = _out("fig_contour_comparison.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {out}")
    return out


# =====================================================================
#  Orchestrator
# =====================================================================
FIGURES = {
    "per_category": fig_retrieval_per_category,
    "heatmap":      fig_retrieval_heatmap,
    "latency":      fig_latency,
    "executability": fig_executability,
    "cfd_results":  fig_cfd_results,
    "contour":      fig_contour_comparison,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help=f"generate only one figure ({', '.join(FIGURES)})")
    args = ap.parse_args()

    _apply_style()
    targets = [args.only] if args.only else list(FIGURES.keys())
    for name in targets:
        if name not in FIGURES:
            print(f"Unknown figure target specified: {name}")
            continue
        print(f"[{name}] Generating...")
        try:
            FIGURES[name]()
        except Exception as e:
            print(f"  [!] Pipeline execution for '{name}' failed: {e}")


if __name__ == "__main__":
    main()
