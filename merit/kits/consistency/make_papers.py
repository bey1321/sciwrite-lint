"""Generate a clean test paper plus variants that each contain ONE planted
internal-consistency error, and write the answer key (expected.json).

Usage:  python make_papers.py   (run automatically by merit/score.py on first use)
Edit VARIANTS below to add your own cases.
"""

import json
from pathlib import Path

BASE = r"""\documentclass{article}
\usepackage{booktabs}
\title{Lightweight Transformers for Early Detection of Network Intrusions}
\author{Test Author}
\begin{document}
\maketitle
\begin{abstract}
Network intrusion detection on edge devices requires models that are both accurate and small.
We propose LiteIDS, a distilled transformer with 4.2M parameters.
Evaluated on 12{,}000 labelled flows, LiteIDS reaches 94.1\% accuracy, improving on the strongest baseline by 2.3 percentage points{ABSTRACT_EXTRA}.
\end{abstract}

\section{Introduction}
Intrusion detection systems (IDS) increasingly run on resource-constrained hardware.
{CONTRIB}

\section{Data and Method}
We collected 12{,}000 labelled flows; after de-duplication, {N_METHOD} flows were used for training and evaluation.
The flows fall into three classes: benign ({P1}\%), denial-of-service ({P2}\%), and probing ({P3}\%).
LiteIDS is trained for 30 epochs with AdamW and evaluated with 5-fold cross-validation.
{METHOD_EXTRA}

\section{Results}
Table~\ref{tab:res} reports accuracy for all models.
LiteIDS achieves {ACC_TEXT}\% accuracy, while the best baseline (DistilBERT-IDS) reaches 91.8\%.
The improvement is statistically significant ($p = {PVAL}$, paired t-test), {P_INTERP}.
{RESULTS_EXTRA}

\begin{table}[h]
\centering
\begin{tabular}{lcc}
\toprule
Model & Params (M) & Accuracy (\%) \\
\midrule
Random Forest & -- & 88.5 \\
DistilBERT-IDS & 66.0 & 91.8 \\
LiteIDS (ours) & 4.2 & 94.1 \\
\bottomrule
\end{tabular}
\caption{Accuracy on the held-out folds.}
\label{tab:res}
\end{table}

\section{Conclusion}
LiteIDS {CONCLUSION}
\end{document}
"""

CLEAN = {
    "ABSTRACT_EXTRA": "",
    "CONTRIB": "This paper makes two contributions: (1) a distilled transformer for IDS, "
    "and (2) an evaluation of its accuracy against standard baselines.",
    "N_METHOD": "12{,}000",
    "P1": "60", "P2": "25", "P3": "15",
    "METHOD_EXTRA": "",
    "ACC_TEXT": "94.1",
    "PVAL": "0.01",
    "P_INTERP": "indicating the gain is unlikely to be due to chance",
    "RESULTS_EXTRA": "",
    "CONCLUSION": "is associated with higher accuracy than larger baselines while using far fewer parameters.",
}

# name -> (overrides, expected check ids)
VARIANTS = {
    "c00_clean": ({}, []),
    "c01_sample_size": ({"N_METHOD": "9{,}400"}, ["sample-size-consistency"]),
    "c02_percentages": ({"P1": "55", "P2": "35", "P3": "20"}, ["percentages-sum"]),
    "c03_numbers_vs_table": ({"ACC_TEXT": "96.4"}, ["numbers-vs-tables"]),
    "c04_abstract_overclaim": (
        {"ABSTRACT_EXTRA": ", and it outperforms every baseline on all five benchmark datasets"},
        ["abstract-body-alignment"],
    ),
    "c05_structure_promises": (
        {"CONTRIB": "This paper makes three contributions: (1) a distilled transformer for IDS, "
         "(2) an evaluation against standard baselines, and (3) a deployment study on a Raspberry Pi 4."},
        ["structure-promises"],
    ),
    "c06_statistics": (
        {"PVAL": "0.38", "P_INTERP": "confirming the gain is statistically significant"},
        ["statistical-reporting"],
    ),
    "c07_causal_language": (
        {"CONCLUSION": "proves that distillation causes better intrusion detection in all edge settings."},
        ["causal-language-audit"],
    ),
    "c08_cross_section": (
        {"RESULTS_EXTRA": "LiteIDS was trained for 50 epochs, which proved necessary for convergence."},
        ["cross-section-consistency"],
    ),
}


def render(overrides: dict) -> str:
    text = BASE
    for k, v in {**CLEAN, **overrides}.items():
        text = text.replace("{" + k + "}", v)
    return text


def main() -> None:
    out = Path("papers")
    out.mkdir(exist_ok=True)
    expected = {}
    for name, (overrides, checks) in VARIANTS.items():
        (out / f"{name}.tex").write_text(render(overrides), encoding="utf-8")
        expected[f"{name}.tex"] = checks
    Path("expected.json").write_text(json.dumps(expected, indent=2))
    print(f"Wrote {len(VARIANTS)} papers to {out}/ and expected.json")


if __name__ == "__main__":
    main()
