---
name: disk-space-analyzer
description: Analyze disk space and find cleanable files. Use when user wants to clean disk, free up space, find large files, analyze disk usage, or asks about what's taking up space. Triggers on requests like "clean my disk", "free up space on C:", "find large files", "what's using my disk space", "disk cleanup".
---

# Disk Space Analyzer

Analyze disk space usage and identify files that can be safely cleaned. **Data source and scripts differ by OS** — do not reuse Windows scripts on macOS or vice versa.

**First: determine the current operating system**, then follow the workflow for that system only.

## System check

Before any workflow steps, determine the OS:

- **Windows**: `sys.platform == "win32"` or user is on Windows.
- **macOS**: `sys.platform == "darwin"` or user is on Mac.

You can run:
```bash
python3 -c "import sys; print(sys.platform)"
```
(`win32` → Windows, `darwin` → macOS)

## Next steps by system

- **If Windows** → Read and follow **[docs/windows.md](docs/windows.md)** for the full workflow (WizTree, scripts in `scripts/windows/`, analysis commands).
- **If macOS** → Read and follow **[docs/macos.md](docs/macos.md)** for the full workflow (different data source and scripts; no WizTree).

**Always visualize in the CLI:** results must be shown to the user as Unicode bar charts pasted into the reply in a ```diff block with `--chat-color` (on macOS: `analyze_disk.py <csv> dashboard` — includes a box-drawing `treemap` disk map — and `--viz` on any command — see docs/macos.md). Don't answer with plain lists of sizes only.

**Every cleanup proposal must be visualized:** whenever you suggest what to delete/move/offload, render it with `analyze_disk.py <csv> plan <plan.json|->` (ranked actions + cumulative freed space + disk gauges now → after) and paste the chart verbatim — never propose cleanup as a bare table or list. Details in docs/macos.md → "Proposing cleanup".

**Every cleanup must end with a before → after visualization:** after deleting anything, rescan and render `analyze_disk.py <after_csv> compare <before_csv>` plus a fresh `dashboard`, pasted verbatim — never report the result as a bare "freed N GB". Details in docs/macos.md → "After cleanup".

**Colored charts in chat:** always run chart commands with `--chat-color` and paste the output in a ```diff block — green lines = the cleanup effect (space freed); no red lines. Always show both the `DISK MAP` treemap and the bar charts (the full `dashboard`), never just one of them.

**Chart language:** chart labels are English by default; add `--lang ru` only when the user asks for Russian charts. Keep this skill's docs in English.

Do not mix: Windows workflow uses `scripts/windows/` (WizTree + CSV analysis). macOS workflow uses its own data source and scripts as described in `docs/macos.md`.
