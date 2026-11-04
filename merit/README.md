# MERIT: running sciwrite-lint's internal-consistency checks without a GPU

This is a fork of [sciwrite-lint](https://github.com/authentic-research-partners/sciwrite-lint) (MIT licence, by Sergey Samsonau / Authentic Research Partners), adapted for the MERIT senior design project at AURAK.

The original tool needs an NVIDIA GPU with 16 GB of memory to run its language models locally. This fork runs the same checks through **OpenRouter**, a hosted API, so they work on an ordinary laptop. It also adds small test kits for measuring how well the checks work.

**Contents**
1. [What's in this fork](#1-whats-in-this-fork)
2. [Requirements](#2-requirements)
3. [Windows only: set up WSL and VS Code](#3-windows-only-set-up-wsl-and-vs-code)
4. [Get the code and install](#4-get-the-code-and-install)
5. [OpenRouter key and model](#5-openrouter-key-and-model)
6. [Connection test](#6-connection-test)
7. [Run the test kits](#7-run-the-test-kits)
8. [Read the results](#8-read-the-results)
9. [Check a real paper](#9-check-a-real-paper)
10. [Add your own test cases](#10-add-your-own-test-cases)
11. [Troubleshooting](#11-troubleshooting)
12. [What was changed, and limitations](#12-what-was-changed-and-limitations)

---

## 1. What's in this fork

| Path | What it is |
|---|---|
| `sciwrite_lint/` | The original tool, with small changes so it can use a hosted API (see [section 12](#12-what-was-changed-and-limitations)) |
| `.env.example` | Template for your **personal** settings: API key and model names |
| `.sciwrite-lint.toml` | **Shared** settings: request limits and vision mode. No secrets. |
| `merit/setup.sh` | One-time environment setup |
| `merit/score.py` | Runs the checks on a test kit and scores them against the answer key |
| `merit/kits/consistency/` | 9 test papers for the text consistency checks |
| `merit/kits/figures/` | 5 test papers with real figure images for the figure checks |

**Checks covered (document-internal consistency):**

| Suite | Checks |
|---|---|
| `consistency` | cross-section-consistency, abstract-body-alignment, numbers-vs-tables, arithmetic-consistency, percentages-sum, sample-size-consistency, statistical-reporting, causal-language-audit, structure-promises |
| `figures` | caption-vs-content, text-vs-figure, axis-label-consistency, figure-data-vs-table |

## 2. Requirements

- **Linux, or Windows with WSL** (Ubuntu inside Windows). The tool is only tested on Linux. macOS is untested.
- About **10 GB of free disk space**. The dependencies include PyTorch.
- An **OpenRouter account**: <https://openrouter.ai>.
- **No GPU needed.**

## 3. Windows only: set up WSL and VS Code

Skip this section on Linux.

1. Open **PowerShell as administrator** and run:
   ```powershell
   wsl --install -d Ubuntu
   ```
   Restart when it asks, then open **Ubuntu** from the Start menu and choose a username and password.
2. If you have **Docker Desktop** installed, make sure Ubuntu (not `docker-desktop`) is the default:
   ```powershell
   wsl -l -v
   wsl --set-default Ubuntu
   ```
3. In **VS Code**, install the **WSL** extension (by Microsoft). Then press `Ctrl+Shift+P` → **WSL: Connect to WSL using Distro...** → **Ubuntu**. The bottom-left corner should show `WSL: Ubuntu`. Open a terminal there with ``Ctrl+` ``.

> **Important:** keep the project inside your Linux home folder (`~/projects/...`), **not** on `/mnt/c/...`, OneDrive or the Desktop. Windows folders are much slower from WSL, and OneDrive tries to sync thousands of library files.
>
> To see your Linux files in Windows File Explorer, open `\\wsl.localhost\Ubuntu\home\<your-username>`.

## 4. Get the code and install

In the Ubuntu terminal:

```bash
# 1. Install uv (Python package manager) - once per machine
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# 2. Get the code
mkdir -p ~/projects && cd ~/projects
git clone https://github.com/bey1321/sciwrite-lint.git
cd sciwrite-lint

# 3. Set everything up (creates .venv, installs pinned dependencies, creates .env)
bash merit/setup.sh
```

Every time you open a new terminal, activate the environment:
```bash
cd ~/projects/sciwrite-lint
source .venv/bin/activate
```
Your prompt then starts with `(.venv)`.

> The setup script installs from `requirements-pinned.txt` on purpose. A plain `pip install` pulls `bibtexparser` 2.x, which crashes the citation check.

## 5. OpenRouter key and model

1. Create a key at <https://openrouter.ai> → **Keys**.
2. Open `.env` in the repository root (the setup script created it) and paste your key:
   ```ini
   OPENROUTER_API_KEY=sk-or-v1-...
   SCIWRITE_LLM_ENDPOINT=https://openrouter.ai/api/v1
   SCIWRITE_VISION_ENDPOINT=https://openrouter.ai/api/v1
   SCIWRITE_LLM_MODEL=nvidia/nemotron-3.5-super-vl:free
   SCIWRITE_VISION_MODEL=nvidia/nemotron-3.5-super-vl:free
   ```
   `.env` is personal and git-ignored. **Never commit it or paste your key anywhere else.**

**Choosing a model.** The model must support *structured outputs* (JSON schema). For the figure checks, the vision model must also accept images. To list the free models that qualify:
```bash
python3 -c "import json,urllib.request; d=json.load(urllib.request.urlopen('https://openrouter.ai/api/v1/models'))['data']; [print(m['id'], m.get('context_length')) for m in d if m['id'].endswith(':free') and 'structured_outputs' in (m.get('supported_parameters') or [])]"
```
Avoid very small models (around 2–3B parameters); they miss a lot. The original author benchmarked with `qwen/qwen3-8b`, which is a paid model but cheap. Use it if you want results comparable to the paper.

**Rate limits for free models:** 20 requests per minute, plus 50 per day. The daily limit rises to 1,000 after a one-time $10 credit purchase on the account.

**Where settings come from** (first match wins):
1. a variable set in the terminal, e.g. `SCIWRITE_LLM_MODEL=qwen/qwen3-8b python merit/score.py consistency`
2. `.env` (in the current folder or any folder above it)
3. `.sciwrite-lint.toml`
4. the tool's built-in defaults

## 6. Connection test

This runs one check on one paper:
```bash
python merit/score.py consistency --papers c02_percentages.tex --checks percentages-sum
```
The first run generates the test papers. You should see `OK`: the paper's class percentages add up to 110%, and the check should catch that.

| You see | Meaning |
|---|---|
| `OK` | Everything works |
| `expected [...] got []` | Connected, but the model missed the error. That is a real result. |
| `tool error` / `not scored` | Key, model name, credits or rate limit. See [Troubleshooting](#11-troubleshooting). |

## 7. Run the test kits

Run from the repository root with `(.venv)` active.

**Everything in a suite:**
```bash
python merit/score.py consistency      # 9 papers x 9 checks, about 85 requests
python merit/score.py figures          # 5 papers x 4 checks, about 25 requests
```

**One paper with its own check** is cheaper and easier to follow:

| Consistency paper | Check | Planted error |
|---|---|---|
| `c00_clean.tex` | *(all 9)* | none; any finding is a false alarm |
| `c01_sample_size.tex` | `sample-size-consistency` | abstract says 12,000 flows, methods say 9,400 |
| `c02_percentages.tex` | `percentages-sum` | class split adds up to 110% |
| `c03_numbers_vs_table.tex` | `numbers-vs-tables` | text says 96.4%, table says 94.1% |
| `c04_abstract_overclaim.tex` | `abstract-body-alignment` | abstract claims 5 datasets, body tests 1 |
| `c05_structure_promises.tex` | `structure-promises` | promises 3 contributions, delivers 2 |
| `c06_statistics.tex` | `statistical-reporting` | p = 0.38 called "significant" |
| `c07_causal_language.tex` | `causal-language-audit` | "proves ... causes" |
| `c08_cross_section.tex` | `cross-section-consistency` | 30 epochs in methods, 50 in results |

| Figure paper | Check | Planted error |
|---|---|---|
| `f00_clean.tex` | *(all 4)* | none; any finding is a false alarm |
| `f01_caption_vs_content.tex` | `caption-vs-content` | caption says accuracy falls, plot rises |
| `f02_text_vs_figure.tex` | `text-vs-figure` | text says it plateaus at 80%, plot reaches 94% |
| `f03_axis_labels.tex` | `axis-label-consistency` | axes say "Training loss" / "minutes", text says accuracy / epochs |
| `f04_figure_vs_table.tex` | `figure-data-vs-table` | bar chart and table disagree |

Example:
```bash
python merit/score.py consistency --papers c01_sample_size.tex --checks sample-size-consistency
python merit/score.py figures --papers f03_axis_labels.tex --checks axis-label-consistency
python merit/score.py figures --papers f00_clean.tex
```

**The repository's own benchmark.** The original author ships 45 test cases for the consistency checks, and it is a stricter test. Run one check at a time:
```bash
python -m evals eval-synthetic --checks percentages-sum
```

## 8. Read the results

Each run prints a table and saves two files in `merit/kits/<suite>/results/` (git-ignored):

- `<timestamp>.csv` contains every finding. Use `--name` to choose the file name.
- `summary.csv` gets one line per run: the model, TP/FP/FN, precision and recall.

| Term | Meaning |
|---|---|
| **TP** (true positive) | the planted error was caught |
| **FN** (false negative) | the planted error was missed |
| **FP** (false positive) | a check fired where nothing was planted |
| **Recall** | caught ÷ (caught + missed) |
| **Precision** | caught ÷ (caught + false alarms) |
| `n/a` | nothing to measure, e.g. a clean paper with no findings. That is a **pass**. |

In the findings CSV, `message` and `context` are written **by the language model**: its description and its quoted evidence. `level` and `rule_id` come from the tool's code. The scorer only checks *which check fired*, so open the CSV and confirm each finding points at the right problem.

Language models give slightly different answers between runs. Repeat a run 2–3 times before trusting a result, and always report the model name.

## 9. Check a real paper

**Use the LaTeX source, not the PDF.** PDFs need GROBID, a separate Docker container, and in this fork the figure checks don't run on PDFs. They report nothing.

**1. Download the source from arXiv.** On the paper's arXiv page, choose **TeX Source**, or use the paper ID:
```bash
mkdir -p ~/papers/2401.12345 && cd ~/papers/2401.12345
wget -O src.tar.gz https://arxiv.org/e-print/2401.12345
if [ -n "$(tar tzf src.tar.gz 2>/dev/null)" ]; then tar xzf src.tar.gz; else gunzip -c src.tar.gz > main.tex; fi
```
(Most papers are an archive of files; a few are a single gzipped `.tex`. The last line handles both.)

**2. Find the main file:** the one with `\begin{document}`.
```bash
grep -l '\\begin{document}' *.tex
```

**3. Merge it into one file.** sciwrite-lint does **not** follow `\input{}` / `\include{}`, so sections in separate files are invisible to it, and labels defined there cause false `dangling-ref` errors. Most arXiv papers are split this way:
```bash
python ~/projects/sciwrite-lint/merit/flatten_tex.py main.tex     # writes main_flat.tex
```

**4. Run the checks** from inside the repository folder, so your `.env` and `.sciwrite-lint.toml` are found:
```bash
cd ~/projects/sciwrite-lint
sciwrite-lint check ~/papers/2401.12345/main_flat.tex --checks numbers-vs-tables,sample-size-consistency
sciwrite-lint check ~/papers/2401.12345/main_flat.tex --checks caption-vs-content,text-vs-figure --format json > out.json
```

**5. Test with a planted error.** Copy `main_flat.tex`, change one thing (a number in the abstract, a value in a table), and check that the right check fires on the copy but not on the original. Findings on the unchanged original are either real problems in the paper or false alarms. Read them and decide.

Notes:
- Figure checks only read **PNG/JPG** images included with `\includegraphics`. PDF, EPS and SVG figures (common on arXiv) are skipped, and you will see a `vision-unavailable` warning. Pick papers with PNG/JPG figures for figure tests.
- Very long papers (roughly 50+ pages) skip the LLM checks.
- `sciwrite-lint checks` lists all check ids.
- **Privacy:** the paper's text and figures are sent to OpenRouter and the model provider. Only use published papers, or papers whose authors agree.

## 10. Add your own test cases

Edit `VARIANTS` in `merit/kits/<suite>/make_papers.py`. Each entry is:
```python
"c09_my_case": ({"PLACEHOLDER": "replacement text"}, ["expected-check-id"]),
```
The placeholders (`{N_METHOD}`, `{ACC_TEXT}`, ...) are in the `BASE` template in the same file. After editing, delete `expected.json` in the kit folder; the next scorer run regenerates the papers.

New figures go in `merit/kits/figures/papers/figures/` as PNG files.

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `uv: command not found` | `source $HOME/.local/bin/env`, or open a new terminal |
| `sciwrite-lint: command not found` | Activate the environment: `source .venv/bin/activate` |
| `tool error` / `llm-unavailable` | Check `OPENROUTER_API_KEY` and the model names in `.env`; check credits at openrouter.ai |
| `No endpoints found` | The model doesn't support structured outputs. Pick another one (see section 5). |
| Error mentioning a "data policy" | On openrouter.ai, open your account's privacy settings and allow free model providers |
| `429` / rate limit | Wait a minute. Lower `max_concurrency` in `.sciwrite-lint.toml`. Check the daily limit. |
| `vision-unavailable` | Figures could not be described: wrong vision model, a non-PNG/JPG figure, or a rate limit. Rerun; failed figures are retried. |
| `vLLM metrics fetch failed (404)` in the log | Harmless (a local-server status check). Ignore. |
| `DEBUG ... duplicate column` lines | Harmless database messages. Ignore. |
| VS Code connects to `docker-desktop` | `wsl --set-default Ubuntu`, then reconnect (section 3) |
| Very slow install or git | You are probably on `/mnt/c/...`; move the project to `~/projects` |

## 12. What was changed, and limitations

Changes to `sciwrite_lint/`, compared with upstream v0.6.1:

- **Hosted API support.** The API key is read from `OPENROUTER_API_KEY`; the original always sent `"dummy"`. Any model id is accepted. Requests to OpenRouter only go to providers that support JSON-schema output (`llm_utils.py`, `eval_claims.py`).
- **Figure checks over an API.** The vision endpoint and model are configurable under `[vision]`, and the key is sent with vision requests (`vision/describe.py`, `config.py`).
- **Quick mode runs the figure step.** `sciwrite-lint check paper.tex` now describes figures first when figure checks are enabled. Before, the figure checks silently returned nothing in this mode (`cli/check.py`).
- **No more cached failures.** Failed figure descriptions (e.g. after a rate limit) are no longer saved as empty and are retried on the next run (`vision/describe.py`).
- **A warning instead of a silent pass.** A `vision-unavailable` warning appears when figures could not be described (`cli/check.py`).
- **Personal settings in `.env`.** The key, models and endpoints come from `.env` or environment variables, which override `.sciwrite-lint.toml` (`config.py`).
- **Benchmark fixes.** `python -m evals eval-synthetic` now reads your config and runs only the checks you name (`evals/synthetic.py`).

Limitations:
- Results depend on the model and are **not directly comparable** to the original paper's numbers unless you use `qwen/qwen3-8b`.
- vLLM-specific "thinking budget" options are sent but probably ignored by hosted providers.
- The test kits are small, short and deliberately obvious. They show the pipeline works, not that the checks are reliable on real manuscripts.
- Not covered here: `internal-consistency-pairs` (needs a local embedding step) and the reference/citation checks.

Credit: the checks, prompts and pipeline are the original authors' work. If you use this in research, cite their paper ([arXiv:2604.08501](https://arxiv.org/abs/2604.08501)). The OpenRouter adapter, the figure-step changes and the MERIT test kits were developed with AI assistance (Claude).
