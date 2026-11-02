"""Score sciwrite-lint's checks against the MERIT test kits.

Each kit is a set of small LaTeX papers: one clean paper plus papers that each
contain ONE planted error, with an answer key (expected.json). This script runs
the checks on each paper and compares what fired with the answer key.

Usage (from the repository root, with the virtual environment active):

    python merit/score.py consistency
    python merit/score.py figures
    python merit/score.py figures --papers f01_caption_vs_content.tex --checks caption-vs-content
    python merit/score.py consistency --name nemotron-run1

Results go to merit/kits/<suite>/results/ (git-ignored):
    <name>.csv       every finding, with the model's explanation
    summary.csv      one line per run: model, TP, FP, FN, precision, recall
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

MERIT_DIR = Path(__file__).resolve().parent
REPO_ROOT = MERIT_DIR.parent
KITS_DIR = MERIT_DIR / "kits"

# Checks each suite runs by default.
SUITES: dict[str, list[str]] = {
    "consistency": [
        "cross-section-consistency",
        "abstract-body-alignment",
        "numbers-vs-tables",
        "arithmetic-consistency",
        "percentages-sum",
        "sample-size-consistency",
        "statistical-reporting",
        "causal-language-audit",
        "structure-promises",
    ],
    "figures": [
        "caption-vs-content",
        "text-vs-figure",
        "axis-label-consistency",
        "figure-data-vs-table",
    ],
}

# Findings meaning "the model was not reached", so the paper can't be scored.
UNAVAILABLE = {"llm-unavailable", "vision-unavailable"}


def ensure_papers(kit: Path) -> None:
    """Generate the kit's papers and answer key if they don't exist yet."""
    if (kit / "expected.json").is_file():
        return
    print(f"Generating test papers in {kit.relative_to(REPO_ROOT)} ...")
    subprocess.run([sys.executable, "make_papers.py"], cwd=kit, check=True)


def model_names() -> tuple[str, str]:
    """The text and vision model the checks will use (after .env overrides)."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from sciwrite_lint.config import load_config

        cfg = load_config()
        return cfg.llm_model, cfg.vision_model or "(local default)"
    except Exception:  # noqa: BLE001 - only used for labelling results
        return "unknown", "unknown"


def run_paper(tex: Path, checks: list[str]) -> list[dict] | None:
    """Run sciwrite-lint on one paper. None means the tool itself failed."""
    proc = subprocess.run(
        [sys.executable, "-m", "sciwrite_lint", "check", str(tex),
         "--checks", ",".join(checks), "--format", "json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if proc.returncode == 2 or not proc.stdout.strip():
        errors = [ln for ln in proc.stderr.splitlines() if "ERROR" in ln or "Tool error" in ln]
        last = (errors or proc.stderr.strip().splitlines() or ["unknown error"])[-1]
        print(f"  !! tool error: {last}")
        return None
    return json.loads(proc.stdout).get("findings", [])


def pct(num: int, den: int) -> str:
    return f"{num / den:.0%}" if den else "n/a"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("suite", choices=sorted(SUITES), help="which test kit to run")
    ap.add_argument("--papers", default="", help="comma-separated paper files (default: all)")
    ap.add_argument("--checks", default="", help="comma-separated check ids (default: the suite's checks)")
    ap.add_argument("--name", default="", help="name for this run's results file")
    args = ap.parse_args()

    kit = KITS_DIR / args.suite
    ensure_papers(kit)
    expected: dict[str, list[str]] = json.loads((kit / "expected.json").read_text())

    checks = [c.strip() for c in args.checks.split(",") if c.strip()] or SUITES[args.suite]
    papers = [p.strip() for p in args.papers.split(",") if p.strip()] or sorted(expected)
    unknown = [p for p in papers if p not in expected]
    if unknown:
        print(f"Unknown paper(s): {', '.join(unknown)}. Available: {', '.join(sorted(expected))}")
        return 2

    text_model, vision_model = model_names()
    print(f"Suite: {args.suite}   text model: {text_model}"
          + (f"   vision model: {vision_model}" if args.suite == "figures" else ""))

    tp, fp, fn = Counter(), Counter(), Counter()
    not_scored: list[str] = []
    rows: list[dict] = []
    for name in papers:
        print(f"Checking {name} ...")
        findings = run_paper(kit / "papers" / name, checks)
        if findings is not None and any(f.get("rule_id") in UNAVAILABLE for f in findings):
            print("  !! model not reached for this paper - not scored")
            findings_for_csv, findings = findings, None
        else:
            findings_for_csv = findings or []
        for f in findings_for_csv:
            rows.append({"model": text_model, "paper": name,
                         **{k: f.get(k, "") for k in ("level", "rule_id", "message", "context")}})
        if findings is None:
            not_scored.append(name)
            continue

        found = {f["rule_id"] for f in findings if f.get("rule_id") in checks}
        want = {c for c in expected.get(name, []) if c in checks}
        for c in found & want:
            tp[c] += 1
        for c in found - want:
            fp[c] += 1
        for c in want - found:
            fn[c] += 1
        print("  OK" if found == want else f"  expected {sorted(want)} got {sorted(found)}")

    # Save findings + append a one-line summary for this run.
    results = kit / "results"
    results.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_name = args.name or stamp
    out = results / f"{run_name}.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "paper", "level", "rule_id", "message", "context"])
        w.writeheader()
        w.writerows(rows)

    T, P, N = sum(tp.values()), sum(fp.values()), sum(fn.values())
    summary = results / "summary.csv"
    new_file = not summary.exists()
    with open(summary, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["time", "run", "text_model", "vision_model", "papers", "checks",
                        "TP", "FP", "FN", "precision", "recall", "not_scored"])
        w.writerow([stamp, run_name, text_model, vision_model if args.suite == "figures" else "",
                    " ".join(papers), " ".join(checks), T, P, N, pct(T, T + P), pct(T, T + N),
                    " ".join(not_scored)])

    print(f"\n{'check':28} {'TP':>3} {'FP':>3} {'FN':>3}")
    for c in checks:
        print(f"{c:28} {tp[c]:>3} {fp[c]:>3} {fn[c]:>3}")
    print(f"\nOverall: precision {pct(T, T + P)}  recall {pct(T, T + N)}")
    print("(n/a = nothing to measure, e.g. a clean paper with no findings - that is a pass)")
    print(f"Findings: {out.relative_to(REPO_ROOT)}   Summary: {summary.relative_to(REPO_ROOT)}")
    if not_scored:
        print(f"WARNING: not scored (model not reached): {', '.join(not_scored)}. "
              "Check your .env key/model and rate limits, then rerun with --papers.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
