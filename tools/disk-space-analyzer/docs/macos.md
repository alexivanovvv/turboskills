# Disk Space Analyzer — macOS

**Use this document only when the current system is macOS.** Data source: Python scan script. Scripts: `scripts/macos/` (macOS-only; do not use Windows scripts or WizTree).

**Run all commands from the skill directory** (the folder that contains `scripts/`). In Cursor, run from the skill folder or a workspace that includes it.

## Workflow Overview

```
1. Select volume/path → 2. Scan and export CSV → 3. Analyze and recommend
```

## Step 1: Choose target volume/path

List mounted volumes and usage:

```bash
df -h
```

Or list disks and volumes:

```bash
diskutil list
```

To get a JSON list of volumes (mount point, total/free space) for scripting:

```bash
python3 scripts/macos/list_volumes.py
```

Common choices:

- **`/`** — whole system volume (scan can be long)
- **`/Users/<username>`** — user home only (recommended first)
- **`/Volumes/<name>`** — other mounted volumes (e.g. external drive)

If the user has not specified a path, show the output of `df -h`, suggest starting with the volume that has the **least free space**, and recommend `/Users/<username>` for a quicker first run.

## Step 2: Scan and export CSV

### Sizes are real on-disk sizes

`scan_disk.py` records `allocated` = `st_blocks × 512`, and all analysis uses it. Cloud placeholders (iCloud Drive, Dropbox, Google Drive files that are not downloaded) have a big logical size but take 0 bytes — they are excluded from totals and reported separately as "☁ cloud-only". CSVs from older scans (where `allocated` = logical size) overstate cloud folders — rescan.

### Permissions note

Scanning may trigger multiple macOS permission dialogs (e.g., Photos, iCloud Drive, Desktop, Documents). To avoid repeated prompts:

1. **One-time solution**: Grant **Full Disk Access** to your terminal app:
   - Open **System Settings → Privacy & Security → Full Disk Access**
   - Add your terminal app (Terminal, iTerm2, Warp, etc.) or IDE (Cursor, VS Code)
   - Restart the terminal after granting access

2. **Alternative**: Click "Allow" for each permission dialog as they appear during the scan.

Without Full Disk Access, some directories may be skipped or show 0 bytes.

From the **skill directory**:

```bash
python3 scripts/macos/scan_disk.py <root_path> <output_csv> [options]
```

**Arguments:**
- **root_path** — e.g. `/`, `/Users/username`, `/Volumes/Data`
- **output_csv** — e.g. `./disk_report.csv` or `<scratchpad>/disk_report.csv`

**Options:**
- **--skip-hidden** — skip files and directories whose name starts with `.` (reduces scan size; default is to include them so caches like `.cache` are analyzed)
- **--max-depth N** — limit scan to N levels deep (useful for quick overview of large directories)
- **--exclude PATTERN** — exclude paths matching pattern (can be used multiple times). Supports glob patterns: `node_modules`, `*.log`, `Library/Caches`

Scanning a large tree can take a long time. Progress is printed to stderr (e.g. every 10,000 entries and every 5 seconds).

**Examples:**

```bash
# Full scan of user home
python3 scripts/macos/scan_disk.py /Users/username ./disk_report.csv

# Quick scan (skip hidden files, limit depth)
python3 scripts/macos/scan_disk.py /Users/username ./disk_report.csv --skip-hidden --max-depth 5

# Skip node_modules and build directories
python3 scripts/macos/scan_disk.py /Users/username ./disk_report.csv --exclude node_modules --exclude build --exclude .git
```

## Step 3: Analyze results

Every command outputs **JSON** by default (for your own reasoning) or **Unicode bar charts** with `--viz` (for the user). `dashboard` always renders charts.

### Visualizations in the CLI — REQUIRED

The user must see charts right in the chat, not just text tables. Bash output is **not** reliably shown to the user, so:

1. Run `dashboard` first (disk fill gauge, treemap disk map, file types, top folders, cleanable split safe/check, largest files).
2. **Paste its output verbatim and in full** into your reply inside a ` ```diff ` code block (run with `--chat-color`) — do not retype, round, or reformat the bars, and never crop sections (`head`/`sed`). The `DISK MAP` treemap must always be shown; on a re-run, show the treemap too, not just the gauge and folder bars.
3. For every follow-up view (drill into a folder, search, filter, largest) run the command with `--viz` and paste that chart the same way, then add your commentary/recommendations *below* the chart.
4. Use plain JSON (no `--viz`) only when you need exact data for your own analysis (e.g. full `migration_hints`, sample file lists in `cleanable`).
5. Do **not** use `--color` (ANSI) for chat output (ANSI codes show up as garbage); it's only for when the user runs the script in their own terminal.
6. **Colors in chat — always:** add `--chat-color` to every chart command whose output goes into the reply, and paste it in a ` ```diff ` block instead of ` ```text `. The CLI highlights whole lines; only **green** (`+` prefix) is used, for the cleanup effect — "after" gauges in `plan`/`compare`, the freed-space Δ bar, folders that shrank. Everything else stays neutral. **No red** — the user finds it too harsh; never prefix lines with `-`. The treemap stays uncolored, but it is always shown alongside the bar charts — never pick one over the other.
7. **Chart language:** labels are English by default. Add `--lang ru` to any command only when the user asks for Russian charts.

### Proposing cleanup — REQUIRED `plan` chart

Whenever you propose what to clean (at the end of analysis, or any time you suggest deleting/moving/offloading something), **do not** write a bare table or bullet list. Write a plan JSON (ordered as you recommend — safe first) and render it:

```bash
cat > <scratchpad>/plan.json <<'JSON'
[
  {"label": "Caches: ~/.cache, ~/.npm", "safety": "safe",  "paths": ["~/.cache", "~/.npm", "~/Library/Caches"]},
  {"label": "Videos in Downloads",      "safety": "check", "paths": ["~/Downloads/big-folder"]},
  {"label": "Photos: optimize storage", "safety": "check", "bytes": 20000000000}
]
JSON
python3 scripts/macos/analyze_disk.py <csv> plan <scratchpad>/plan.json   # or pipe JSON to `plan -`
```

- `paths` — size is summed from the CSV (real on-disk size); `bytes` — for things measured elsewhere (`du -sk`, Photos, Time Machine snapshots).
- `safety`: `safe` (regenerates), `check` (user must review), `admin` (needs sudo / System Settings).
- Labels ≤ 30 chars, in the chart language (English unless `--lang ru`).

Output: ranked actions with bars and cumulative freed space (Σ), then disk gauges **now → + safe only → + whole plan**. Paste it verbatim in a ` ```diff ` block (`--chat-color`); put commands and caveats for each action *below* the chart. When the user picks a subset, re-render `plan` with only the chosen items before executing.

### After cleanup — REQUIRED `compare` chart

Once approved items are deleted, **always** show the result visually — never just a "freed N GB" sentence:

1. Keep the original CSV (`<csv>`, the "before" scan). Rescan the same root into a new file: `scan_disk.py <root> <after_csv>`.
2. Run `analyze_disk.py <after_csv> compare <csv>` with `--chat-color` and paste it verbatim in a ` ```diff ` block: disk gauges **before → after**, the Δ bar with total freed space, and a per-folder list of what shrank (▼) or grew (▲) with `before → after` sizes. `--depth N` sets the folder level (default 2), `--limit N` the number of rows (default 12).
3. Run `analyze_disk.py <after_csv> dashboard` and paste it too, so the user sees the new disk map.
4. Below the charts: what was deleted, what will come back on its own (caches, re-downloaded models), and what is left as the next-biggest candidate.

`scan_disk.py` saves disk usage at scan time to `<csv>.disk.json`, so `compare` shows exact before/after free space. If the "before" CSV has no such file (older scan), the before gauge is estimated from the scan difference and marked "(est. from scans)".

### Quick start (recommended order)

```bash
# 1. Visual overview → paste into reply
python3 scripts/macos/analyze_disk.py <csv> dashboard [--limit 8]

# 2. Quick wins — details for recommendations (JSON for you, --viz for the user)
python3 scripts/macos/analyze_disk.py <csv> cleanable
python3 scripts/macos/analyze_disk.py <csv> cleanable --viz

# 3. Drill down → paste charts
python3 scripts/macos/analyze_disk.py <csv> folder "<path>" --viz
python3 scripts/macos/analyze_disk.py <csv> largest --limit 20 --viz
python3 scripts/macos/analyze_disk.py <csv> top-folders --depth 2 --viz

# 4. Proposal → paste chart (see "Proposing cleanup")
python3 scripts/macos/analyze_disk.py <csv> plan <plan.json>

# 5. After the user-approved cleanup → rescan + paste result charts (see "After cleanup")
python3 scripts/macos/scan_disk.py <root> <after_csv>
python3 scripts/macos/analyze_disk.py <after_csv> compare <csv>
python3 scripts/macos/analyze_disk.py <after_csv> dashboard
```

Example of `dashboard` output (abridged):

```text
── DISK ────────────────────────────────────────────────────────── volume / ──
 ███████████████████████████████████▌░░░░  89% used
 used 202.5 GB of 228.2 GB  ·  free 25.8 GB

── FOLDERS · level 1 ─────────────────────────────────────────────────────────
 Media                            ██████████████████████    1.9 GB    6%
 Screenshots                      ███████████               950.4 MB  3%

── CLEANABLE ────────────────────────────────────────────────────── 36.6 MB ──
 ████████████████████████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
 █ safe         20.1 MB   ▒ review      16.5 MB
```

### Available commands

#### `dashboard` — one-screen visual overview

```bash
python3 scripts/macos/analyze_disk.py <csv> dashboard [--limit N]
```

Always rendered as charts. `--limit` = rows per section (default 8).

#### `treemap` — disk map in box-drawing characters

```bash
python3 scripts/macos/analyze_disk.py <csv> treemap [--height N]
```

Squarified treemap: area = on-disk size. Top-level folders are double-bordered (`╔═ Library 46 GB ═╗`, name in the frame), their subfolders light-bordered inside; each top-level folder gets its own hatching (`╱ · ╲ ░ …`), labels sit on a clean pad, `░` = small leftovers. Always rendered; included in `dashboard`. Use it when the user asks "where did my space go" — and after drilling into a folder, scan that folder and show its own treemap.

#### `compare` — cleanup result, before → after

```bash
python3 scripts/macos/analyze_disk.py <after_csv> compare <before_csv> [--depth N] [--limit N]
```

Always rendered as charts. See "After cleanup".

#### `summary` — disk overview

```bash
python3 scripts/macos/analyze_disk.py <csv> summary
```

Shows: total size, file count, directory count, top extensions by size.

#### `cleanable` — find cleanable files with reasons

```bash
python3 scripts/macos/analyze_disk.py <csv> cleanable
```

Identifies temp files, caches, logs, dev artifacts, etc., with explanations and migration suggestions.

#### `largest` — largest files

```bash
python3 scripts/macos/analyze_disk.py <csv> largest [--limit N]
```

Default: top 20 files by size.

#### `by-type` — space by extension

```bash
python3 scripts/macos/analyze_disk.py <csv> by-type [--limit N]
```

Shows which file types use the most space.

#### `top-folders` — largest folders by depth

```bash
python3 scripts/macos/analyze_disk.py <csv> top-folders [--depth N] [--limit N]
```

Shows largest folders at each depth level **relative to the scan root** (default depth: 2). Useful for hierarchical exploration.

Example (if scanned from `/`):

- Depth 1: `/Users` (450 GB), `/Applications` (80 GB), …
- Depth 2: `/Users/username` (448 GB), `/Applications/Xcode.app` (15 GB), …

Example (if scanned from `/Users/username`):

- Depth 1: `Library` (12 GB), `Projects` (5 GB), `Downloads` (2 GB), …
- Depth 2: `Library/Caches` (8 GB), `Library/Application Support` (3 GB), …

#### `folder` — explore a specific folder

```bash
python3 scripts/macos/analyze_disk.py <csv> folder "<path>" [--depth N]
```

Shows contents of a folder with size breakdown. Depth controls how many levels to show (default: 1).

Example:

```bash
python3 scripts/macos/analyze_disk.py disk_report.csv folder "/Users/username/Library/Caches" --depth 2
```

#### `search` — search by pattern

```bash
python3 scripts/macos/analyze_disk.py <csv> search "<pattern>"
```

Glob-style pattern (`*`, `?`). Examples:

- `*.log` — all .log files
- `node_modules` — all node_modules directories
- `*backup*` — names containing "backup"

#### `filter` — advanced filtering

```bash
python3 scripts/macos/analyze_disk.py <csv> filter "<conditions>"
```

Sizes accept units (`500MB`, `1.5GB`). Conditions: `size>1GB`, `ext=.log`, `path~Downloads`, `name~backup`  
Operators: `>`, `<`, `>=`, `<=`, `=`, `~` (contains)

Examples:

```bash
python3 scripts/macos/analyze_disk.py disk_report.csv filter "size>1GB,ext=.log"
python3 scripts/macos/analyze_disk.py disk_report.csv filter "path~Downloads,size>100MB"
```

## Cleanable categories (macOS)

| Category   | Examples                                      | Safety   | Notes                          |
|-----------|------------------------------------------------|----------|--------------------------------|
| temp      | .tmp, .temp, ~files                            | Safe     | Regenerates on demand          |
| cache     | ~/Library/Caches, .cache, .npm, pip/uv/HF      | Safe     | Often relocatable              |
| log       | .log, ~/Library/Logs                           | Check    | Check if needed for debugging  |
| backup    | .bak, .old, .orig                              | Check    | May be important backups       |
| dev       | node_modules, __pycache__, .venv, .idea, build | Safe     | Recreate with install/build    |
| browser   | Safari, app caches                             | Safe     | Regenerates                    |
| system    | .DS_Store, CloudKit cache                      | Check    | System/cloud caches            |
| recycle   | .Trash                                         | Check    | Empty Trash in Finder          |
| download  | .dmg, .pkg, .zip in Downloads                  | Check    | Review before deleting         |
| duplicate | (1).jpg, copy.png                             | Check    | Verify before deleting         |

## Cache migration suggestions (macOS)

Many caches can be moved to another volume. The `cleanable` command suggests these when detected:

| Cache     | Default location (macOS)           | How to relocate                          |
|-----------|------------------------------------|------------------------------------------|
| npm      | `~/.npm` / npm-cache               | `npm config set cache ~/cache/npm`       |
| pip      | `~/.cache/pip`                     | Set `PIP_CACHE_DIR` env var              |
| uv       | `~/.cache/uv`                      | Set `UV_CACHE_DIR` env var              |
| Yarn     | `~/.yarn/cache`                    | `yarn config set cache-folder ~/cache/yarn` |
| pnpm     | `~/.pnpm/store`                    | `pnpm config set store-dir ~/cache/pnpm` |
| Cargo    | `~/.cargo/registry`                | Set `CARGO_HOME` env var                 |
| HuggingFace | `~/.cache/huggingface`           | Set `HF_HOME` env var                    |
| Docker   | Docker Desktop data                | Docker Desktop → Settings → Resources    |

## System / special files (macOS)

These are **not** removed by the skill; manage them via system settings or documentation.

- **sleepimage** — hibernation image (e.g. under `/var/vm`). Size ~ RAM. Managed by system; avoid deleting by hand.
- **swapfile** — swap files. Managed by macOS.
- **Time Machine local snapshots** — `tmutil listlocalsnapshots`; remove with `tmutil deletelocalsnapshots <date>` or System Settings → General → Storage.
- **System volumes** — avoid deleting files in `/System`, `/Library`, or other system paths; use System Settings or official tools.

## Workflow tips

1. **Start with `cleanable`** — low-risk quick wins.
2. **Use `top-folders --depth 2`** — see where space is used.
3. **Drill down with `folder`** — inspect specific directories.
4. **Use `filter`** — find specific patterns (size, extension, path).

## Cleanup

After analysis (and the `compare` chart, if anything was cleaned) is complete, delete the temporary CSVs and their snapshots, or remind the user to:

```bash
rm <output_csv> <output_csv>.disk.json
# e.g. rm ./disk_report.csv ./disk_report.csv.disk.json
```

The CSV can be large (tens to hundreds of MB) and is no longer needed once analysis is done.

## Deletion guidelines

**Do not delete files automatically.** Instead:

1. Present results as pasted `--viz` charts plus clear explanations and safety levels; the proposal itself as a pasted `plan` chart.
2. Let the user decide what to delete.
3. For batch deletion, provide **bash/zsh** commands they can run themselves, for example:

   ```bash
   # Example: remove .tmp files in a directory
   find /path/to/dir -name "*.tmp" -type f -delete

   # Example: clear npm cache
   npm cache clean --force

   # Example: remove a cache directory (review path first)
   rm -rf ~/Library/Caches/SomeApp
   ```

4. Warn about system directories and permissions (e.g. `sudo`, `/System`, `/Library`). Prefer user-level paths like `~/Library/Caches` and app-specific cleanup commands.
