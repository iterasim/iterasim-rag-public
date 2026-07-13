"""Emit a per-case LaTeX table for the paper, mirroring the layout
used in MetaOpenFOAM's Table 1 but populated with the metrics we
have actually measured (retrieval tier).

Output: per_case_table.tex (long-form table, 28 cases + per-category
averages + overall row).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
QUERIES = HERE.parent / "benchmark" / "benchmark_queries.json"
# By default look for a results/ folder alongside this script.  Set the
# ITERASIM_RESULTS_ROOT environment variable to override.
import os
RESULTS_ROOT = Path(os.environ.get(
    "ITERASIM_RESULTS_ROOT",
    str(HERE.parent / "results"),
))


def latest_records() -> tuple[list[dict], list[dict]]:
    runs = sorted(p for p in RESULTS_ROOT.iterdir()
                  if p.is_dir() and p.name.startswith("2026"))
    if not runs:
        sys.exit("No eval results found.")
    payload = json.loads((runs[-1] / "results.json").read_text())
    queries = json.loads(QUERIES.read_text())
    records = []
    for r in payload["retrieval"]:
        q = queries[r["idx"] - 1]
        records.append({**r, **q})
    return records, queries


SHORT_TITLE = {
    "A1": "Cavity flow",
    "A2": "PitzDaily",
    "A3": "Hotroom",
    "A4": "Dam break",
    "A5": "Particle column",
    "A6": "Mixed vessel",
    "B1": "Cavity $\\to$ PitzDaily",
    "B2": "PitzDaily $\\to$ Hotroom",
    "B3": "Cavity $\\to$ unsteady",
    "B4": "DamBreak $\\to$ bubble",
    "C1":  "Cavity: $U_{\\mathrm{top}}$ change",
    "C2":  "Cavity: unsteady BC",
    "C3":  "PitzDaily: mesh $\\times 2$",
    "C4":  "Hotroom: $T$-BC change",
    "C5":  "Hotroom: fluid swap",
    "C6":  "DamBreak: column shift",
    "C7":  "DamBreak: oil swap",
    "C8":  "Particle: size/density",
    "C9":  "MixedVessel: $\\omega$ change",
    "C10": "PitzDaily: endTime",
    "D1": "$k$-$\\varepsilon \\to$ RNG",
    "D2": "$k$-$\\varepsilon \\to k$-$\\omega$ SST",
    "D3": "$k$-$\\varepsilon \\to$ LRR RSM",
    "D4": "$k$-$\\varepsilon \\to k$-$k_L$-$\\omega$",
    "D5": "Laminar $\\to k$-$\\varepsilon$",
    "D6": "LES dyn$K \\to$ Smagorinsky",
    "D7": "Hotroom kEps $\\to$ SST",
    "D8": "MixedVessel + $k$-$\\varepsilon$",
}


def _solver_tt(s: str) -> str:
    if not s or s == "any":
        return "--"
    return r"\texttt{" + s + "}"


def _tick(score: float) -> str:
    return r"$\checkmark$" if score >= 0.99 else r"--"


def _row(r: dict) -> str:
    cid = r["case_id"]
    title = SHORT_TITLE.get(cid, r["title"][:24])
    return (
        f"{cid} & {title} & "
        f"{_solver_tt(r['expected_solver'])} & "
        f"{r['score_pct']:5.1f} & "
        f"{r['tag_coverage']*100:5.1f} & "
        f"{_tick(r['solver_match'])} & "
        f"{r['retrieval_seconds']:.2f} \\\\"
    )


def _avg_row(cat: str, rows: list[dict]) -> str:
    n = len(rows)
    mscore = mean(r["score_pct"] for r in rows)
    mcov = mean(r["tag_coverage"] * 100 for r in rows)
    msolver = sum(1 for r in rows if r["solver_match"] >= 0.99)
    mlat = mean(r["retrieval_seconds"] for r in rows)
    return (
        f"\\textbf{{Avg.\\ {cat}}} & ($n={n}$) & -- & "
        f"\\textbf{{{mscore:5.1f}}} & \\textbf{{{mcov:5.1f}}} & "
        f"\\textbf{{{msolver}/{n}}} & \\textbf{{{mlat:.2f}}} \\\\"
    )


def main() -> None:
    records, _ = latest_records()
    if len(records) != 28:
        print(f"warning: got {len(records)} records, expected 28")

    by_cat = {c: sorted([r for r in records if r["category"] == c],
                        key=lambda x: int(x["case_id"][1:]))
              for c in ["A", "B", "C", "D"]}

    lines = []
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Per-case retrieval-tier results on "
                 r"the 28-case IteraSim-LLM benchmark. All "
                 r"columns are measured against the released "
                 r"benchmark using Eq.~(\ref{eq:retr-score}): "
                 r"$s$ is the overall retrieval score, $\tau$ "
                 r"is tag coverage, \emph{Solver} marks whether "
                 r"the expected solver name appears in the "
                 r"retrieved context, and $t_{\mathrm{r}}$ is "
                 r"the end-to-end retrieval latency. "
                 r"Execution-tier results (executability score, "
                 r"token consumption, Reviewer iterations, "
                 r"Pass@1) are reported separately in "
                 r"Sec.~\ref{subsec:exec} on completion of the "
                 r"full toolchain run.}")
    lines.append(r"\label{tab:per-case}")
    lines.append(r"\footnotesize")
    lines.append(r"\setlength{\tabcolsep}{4pt}")
    lines.append(r"\begin{tabular}{l l l r r c r}")
    lines.append(r"\toprule")
    lines.append(r"\multicolumn{3}{c}{\textbf{Case}} & "
                 r"\multicolumn{4}{c}{\textbf{Retrieval-tier "
                 r"metrics (measured)}} \\")
    lines.append(r"\cmidrule(lr){1-3}\cmidrule(lr){4-7}")
    lines.append(r"ID & Title & Solver & "
                 r"$s$ (\%) & $\tau$ (\%) & Solver & $t_{\mathrm{r}}$ (s) \\")
    lines.append(r"\midrule")

    for cat in ["A", "B", "C", "D"]:
        for r in by_cat[cat]:
            lines.append(_row(r))
        lines.append(r"\cmidrule(l){1-7}")
        lines.append(_avg_row(cat, by_cat[cat]))
        lines.append(r"\cmidrule(l){1-7}")

    overall = [r for c in ["A", "B", "C", "D"] for r in by_cat[c]]
    lines.append(r"\midrule")
    lines.append(_avg_row("overall", overall).replace(
        r"\textbf{Avg.\ overall}", r"\textbf{Overall}"))
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    out = PAPER / "per_case_table.tex"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
