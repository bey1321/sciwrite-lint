"""Merge a multi-file LaTeX paper into one .tex file.

sciwrite-lint only reads the file you give it: it does not follow \\input{},
\\include{} or \\subfile{}. Sections kept in separate files are invisible to the
checks, and labels defined there produce false "dangling-ref" errors. Most arXiv
papers are split this way, so flatten them first.

Usage:
    python merit/flatten_tex.py path/to/main.tex            # writes main_flat.tex next to it
    python merit/flatten_tex.py path/to/main.tex -o out.tex

The flattened file stays in the same folder as main.tex, so figure paths in
\\includegraphics keep working.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INCLUDE_RE = re.compile(r"\\(input|include|subfile)\s*\{([^}]+)\}")


def strip_comment(line: str) -> str:
    """Drop a LaTeX comment (an unescaped %) from one line."""
    for i, ch in enumerate(line):
        if ch == "%" and (i == 0 or line[i - 1] != "\\"):
            return line[:i]
    return line


def resolve(name: str, base: Path) -> Path | None:
    path = (base / name.strip()).resolve()
    for candidate in (path, path.with_name(path.name + ".tex")):
        if candidate.is_file():
            return candidate
    return None


def flatten(tex: Path, root: Path, seen: set[Path], missing: list[str]) -> str:
    """Return tex's text with every \\input/\\include/\\subfile expanded in place."""
    if tex in seen:  # guard against include loops
        return ""
    seen = seen | {tex}
    out: list[str] = []
    for line in tex.read_text(encoding="utf-8", errors="replace").splitlines():
        code = strip_comment(line)
        if not INCLUDE_RE.search(code):
            out.append(line)
            continue

        def expand(m: re.Match[str]) -> str:
            target = resolve(m.group(2), root)
            if target is None:
                missing.append(m.group(2))
                return m.group(0)
            body = flatten(target, root, seen, missing)
            if m.group(1) == "subfile":  # keep only the subfile's document body
                inner = re.search(r"\\begin\{document\}(.*)\\end\{document\}", body, re.S)
                body = inner.group(1) if inner else body
            return f"\n% ---- begin {m.group(2)} ----\n{body}\n% ---- end {m.group(2)} ----\n"

        out.append(INCLUDE_RE.sub(expand, code))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge \\input/\\include files into one .tex")
    ap.add_argument("main", type=Path, help="the paper's main .tex file")
    ap.add_argument("-o", "--output", type=Path, help="output file (default: <main>_flat.tex)")
    args = ap.parse_args()

    main_tex = args.main.resolve()
    if not main_tex.is_file():
        print(f"Not found: {args.main}")
        return 1
    missing: list[str] = []
    text = flatten(main_tex, main_tex.parent, set(), missing)
    out = args.output or main_tex.with_name(main_tex.stem + "_flat.tex")
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out}")
    if missing:
        print("Could not find (left as-is): " + ", ".join(sorted(set(missing))), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
