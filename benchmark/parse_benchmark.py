"""Parse benchmark_test_plan.md into a structured query list.

Captures every case in categories A / B / C / D, including the
Category C entries that use ``**Modification prompt:**`` instead of
``**Prompt:**``.  For each case we record the explicit success-related
fields the test plan exposes (expected files, key-check phrases,
declared expected solver) so that the downstream evaluator can score
retrieval against case-specific tags rather than a generic
``openfoam`` token.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "benchmark_test_plan.md"
OUT  = HERE / "benchmark_queries.json"

# Headings look like:   "### A1 — Cavity Flow (Laminar, Incompressible)"
HEADING_RE = re.compile(
    r"^###\s+([ABCD])(\d{1,2})\s+[—-]\s+(.+?)\s*$", re.MULTILINE
)
PROMPT_RE = re.compile(
    r"\*\*(?:Modification\s+prompt|Prompt)[:]\*\*\s*\n```\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)
SOLVER_RE = re.compile(r"\*\*Solver[:]\*\*\s*`([^`]+)`")
EXPECTED_FILES_RE = re.compile(
    r"\*\*Expected files[:]\*\*\s*(.+?)(?:\n|$)", re.IGNORECASE,
)
FILES_TO_CHECK_RE = re.compile(
    r"\*\*Files to check[:]\*\*\s*(.+?)(?:\n|$)", re.IGNORECASE,
)
KEY_CHECK_RE = re.compile(
    r"\*\*Key check[:]\*\*\s*(.+?)(?:\n|$)", re.IGNORECASE,
)


def _extract_inline_codes(text: str) -> list[str]:
    """Return every backticked token in ``text``, lower-cased."""
    return [c.lower() for c in re.findall(r"`([^`]+)`", text or "")]


def _solver_from_prompt(prompt: str) -> str | None:
    """Heuristically pull an OpenFOAM solver name from the prompt."""
    m = re.search(r"\b([a-z][a-zA-Z]*Foam)\b", prompt)
    return m.group(1) if m else None


def parse() -> list[dict]:
    text = PLAN.read_text()
    # Build a list of (start_offset, end_offset, category, idx, title)
    headings = list(HEADING_RE.finditer(text))
    if not headings:
        raise SystemExit("No case headings found in benchmark plan.")

    bounds = []
    for i, m in enumerate(headings):
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        bounds.append((m.group(1), m.group(2), m.group(3).strip(),
                       text[start:end]))

    records: list[dict] = []
    for category, idx, title, block in bounds:
        prompt_m = PROMPT_RE.search(block)
        if not prompt_m:
            # Some sections (e.g., the comparison table at the end) have
            # no prompt — that is fine, we skip silently.
            continue
        prompt = prompt_m.group(1).strip()

        expected_files = _extract_inline_codes(
            (EXPECTED_FILES_RE.search(block) or
             FILES_TO_CHECK_RE.search(block) or
             re.match(r"$.^", "")).group(1)
            if (EXPECTED_FILES_RE.search(block)
                or FILES_TO_CHECK_RE.search(block))
            else ""
        )
        key_check_codes = _extract_inline_codes(
            (KEY_CHECK_RE.search(block) or
             re.match(r"$.^", "")).group(1)
            if KEY_CHECK_RE.search(block) else ""
        )
        solver_m = SOLVER_RE.search(block)
        explicit_solver = (solver_m.group(1).lower()
                           if solver_m else None)
        inferred_solver = _solver_from_prompt(prompt)
        expected_solver = (explicit_solver or inferred_solver
                           or "any")

        # Expected physics tags = expected files ∪ key-check codes
        # ∪ the solver, lower-cased and deduplicated.
        tags = set(expected_files) | set(key_check_codes)
        if expected_solver and expected_solver != "any":
            tags.add(expected_solver.lower())
        # Always include the umbrella tool tag so we keep the original
        # coarse-grained metric available too.
        tags.add("openfoam")

        records.append({
            "case_id": f"{category}{idx}",
            "category": category,
            "title": title,
            "tool": "openfoam",
            "query": prompt,
            "expected_solver": expected_solver,
            "expected_files": expected_files,
            "expected_key_checks": key_check_codes,
            "expected_physics_tags": sorted(tags),
            # Field kept for backwards-compatibility with run_evaluation.
            "expected_primary_intent": "solver_config",
        })

    return records


def main() -> None:
    records = parse()
    OUT.write_text(json.dumps(records, indent=2))
    by_cat: dict[str, int] = {}
    for r in records:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    print(f"Extracted {len(records)} cases: " +
          ", ".join(f"{k}={v}" for k, v in sorted(by_cat.items())))


if __name__ == "__main__":
    main()
