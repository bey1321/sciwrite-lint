"""Generate figure-check test papers: one clean paper plus variants that each
contain ONE planted figure inconsistency. Writes papers/*.tex + expected.json.

The PNG figures in papers/figures/ are shipped with the kit:
  accuracy_curve.png             accuracy rises from ~73% to ~94% over 30 epochs
  accuracy_curve_wrong_axes.png  same curve, but axes say "Training time (minutes)"
                                 and "Training loss"
  model_accuracy.png             bars: Random Forest 88.5, DistilBERT-IDS 91.8, LiteIDS 94.1

Usage:  python make_papers.py   (run automatically by merit/score.py on first use)
Edit VARIANTS below to add your own cases.
"""

import json
from pathlib import Path

BASE = r"""\documentclass{article}
\usepackage{graphicx}
\usepackage{booktabs}
\title{Lightweight Transformers for Early Detection of Network Intrusions}
\author{Test Author}
\begin{document}
\maketitle
\begin{abstract}
We propose LiteIDS, a distilled transformer with 4.2M parameters for intrusion detection on edge devices,
and compare it with two standard baselines.
\end{abstract}

\section{Introduction}
Intrusion detection systems increasingly run on resource-constrained hardware, where small models are essential.

\section{Method}
LiteIDS is trained for 30 epochs with AdamW on 12{,}000 labelled network flows and evaluated with 5-fold cross-validation.

\section{Results}
{CURVE_TEXT}

\begin{figure}[h]
\centering
\includegraphics[width=0.8\linewidth]{figures/{CURVE_IMAGE}}
\caption{{CURVE_CAPTION}}
\label{fig:curve}
\end{figure}

Figure~\ref{fig:models} and Table~\ref{tab:res} compare LiteIDS with the two baselines.

\begin{figure}[h]
\centering
\includegraphics[width=0.8\linewidth]{figures/model_accuracy.png}
\caption{Accuracy of each model on the held-out folds.}
\label{fig:models}
\end{figure}

\begin{table}[h]
\centering
\begin{tabular}{lcc}
\toprule
Model & Params (M) & Accuracy (\%) \\
\midrule
Random Forest & -- & {RF_ACC} \\
DistilBERT-IDS & 66.0 & {DB_ACC} \\
LiteIDS (ours) & 4.2 & {LITE_ACC} \\
\bottomrule
\end{tabular}
\caption{Accuracy on the held-out folds.}
\label{tab:res}
\end{table}

\section{Conclusion}
LiteIDS offers a strong accuracy--size trade-off for edge deployment.
\end{document}
"""

CLEAN = {
    "CURVE_TEXT": r"Figure~\ref{fig:curve} shows validation accuracy rising quickly over the first ten "
    r"epochs and levelling off near 94\% by epoch 30.",
    "CURVE_IMAGE": "accuracy_curve.png",
    "CURVE_CAPTION": r"Validation accuracy (\%) of LiteIDS over 30 training epochs.",
    "RF_ACC": "88.5",
    "DB_ACC": "91.8",
    "LITE_ACC": "94.1",
}

# name -> (overrides, expected check ids)
VARIANTS = {
    "f00_clean": ({}, []),
    "f01_caption_vs_content": (
        {"CURVE_CAPTION": r"Validation accuracy of LiteIDS decreases steadily during training, "
         r"falling below 75\% by epoch 30."},
        ["caption-vs-content"],
    ),
    "f02_text_vs_figure": (
        {"CURVE_TEXT": r"As Figure~\ref{fig:curve} shows, validation accuracy plateaus at about 80\% "
         r"after epoch 5 and does not improve with further training."},
        ["text-vs-figure"],
    ),
    "f03_axis_labels": (
        {"CURVE_IMAGE": "accuracy_curve_wrong_axes.png"},
        ["axis-label-consistency"],
    ),
    "f04_figure_vs_table": (
        {"RF_ACC": "90.2", "DB_ACC": "87.4", "LITE_ACC": "89.0"},
        ["figure-data-vs-table"],
    ),
}


def render(overrides: dict) -> str:
    text = BASE
    for key, value in {**CLEAN, **overrides}.items():
        text = text.replace("{" + key + "}", value)
    return text


def main() -> None:
    out = Path("papers")
    if not (out / "figures").is_dir():
        raise SystemExit("papers/figures/ is missing - unzip the kit with its figures folder.")
    expected = {}
    for name, (overrides, checks) in VARIANTS.items():
        (out / f"{name}.tex").write_text(render(overrides), encoding="utf-8")
        expected[f"{name}.tex"] = checks
    Path("expected.json").write_text(json.dumps(expected, indent=2))
    print(f"Wrote {len(VARIANTS)} papers to {out}/ and expected.json")


if __name__ == "__main__":
    main()
