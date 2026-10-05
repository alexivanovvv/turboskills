#!/usr/bin/env python3
"""
Analyze macOS scan CSV to find cleanable files and disk usage.

Usage:
    python3 scripts/macos/analyze_disk.py <csv_path> <command> [options]

Commands:
    dashboard [--limit N]       One-screen visual overview (always rendered as charts)
    summary                     Show disk usage summary
    largest [--limit N]         Show largest files (default: 20)
    by-type [--limit N]         Show space usage by file type
    cleanable                   Find potentially cleanable files with reasons
    top-folders [--depth N]     Show largest folders at each depth level
    folder <path> [--depth N]   Explore specific folder contents
    search <pattern>            Search files by name pattern
    filter <conditions>         Filter by conditions (see examples)
    treemap [--height N]        Box-drawing treemap: folders as nested rectangles (always charts)
    plan <plan.json|->          Visualize a cleanup proposal (always rendered as charts)
    compare <before.csv>        Cleanup result: disk before → after + per-folder deltas
                                (run on the AFTER csv; --depth N, --limit N; always charts)

Output options (any command):
    --viz                       Render Unicode bar charts instead of JSON
    --color                     Add ANSI colors (only for a real terminal, not for chat)
    --lang ru                   Chart labels in Russian (default: English)
    --chat-color                Prefix lines for a ```diff block in chat: "+" green = cleanup
                                effect (freed space, disk after); no red

CSV format (from scan_disk.py): path,size,allocated,modified,is_dir,files_count,folders_count
Paths are POSIX (e.g. /Users/jane/...). Run from the skill directory.
"""

import csv
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Tuple

import viz

# Output mode: "json" (default), "viz" (--viz), "silent" (used by dashboard)
MODE = "viz" if "--viz" in sys.argv else "json"
VIZ_RENDERERS = {
    "summary": lambda r: viz.render_summary(r),
    "largest": lambda r: viz.render_largest(r),
    "by-type": lambda r: viz.render_by_type(r),
    "top-folders": lambda r: viz.render_top_folders(r),
    "folder": lambda r: viz.render_folder(r),
    "cleanable": lambda r: viz.render_cleanable(r),
    "search": lambda r: viz.render_search(r),
    "filter": lambda r: viz.render_search(r),
}

FREE_SPACE_PATH = "/System/Volumes/Data" if Path("/System/Volumes/Data").exists() else "/"


def emit(command: str, result: Any) -> None:
    if MODE == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif MODE == "viz":
        print(viz.join(VIZ_RENDERERS[command](result)))


# macOS cleanable patterns: (regex, category, reason, migration_hint). Use / for path sep.
CLEANABLE_PATTERNS = [
    # Temp / backup
    (r"\.tmp$", "temp", "Temporary file", None),
    (r"\.temp$", "temp", "Temporary file", None),
    (r"~$", "temp", "Temporary/backup file", None),
    (r"\.bak$", "backup", "Backup file", None),
    (r"\.old$", "backup", "Old version backup", None),
    (r"\.orig$", "backup", "Original backup", None),
    # Cache
    (r"Library/Caches", "cache", "Application caches", None),
    (r"\.cache/", "cache", "Cache directory", None),
    (r"\.npm/", "cache", "npm cache", "npm config set cache ~/cache/npm"),
    (r"npm-cache", "cache", "npm cache", "npm config set cache ~/cache/npm"),
    (r"\.yarn/cache", "cache", "Yarn cache", "yarn config set cache-folder ~/cache/yarn"),
    (r"\.pnpm/store", "cache", "pnpm store", "pnpm config set store-dir ~/cache/pnpm"),
    (r"\.cargo/registry/", "cache", "Cargo (Rust) cache", "Set CARGO_HOME env var"),
    (r"\.gradle/caches", "cache", "Gradle cache", "Set GRADLE_USER_HOME env var"),
    (r"\.m2/repository", "cache", "Maven cache", "Set in settings.xml localRepository"),
    (r"\.cache/pip", "cache", "pip cache", "Set PIP_CACHE_DIR env var"),
    (r"\.cache/uv", "cache", "uv (Python) cache", "Set UV_CACHE_DIR env var"),
    (r"\.cache/huggingface", "cache", "HuggingFace models", "Set HF_HOME env var"),
    (r"\.cache/torch", "cache", "PyTorch cache", "Set TORCH_HOME env var"),
    (r"\.ollama/models", "cache", "Ollama models", "Set OLLAMA_MODELS env var"),
    (r"\.cache/go-build", "cache", "Go build cache", "Set GOCACHE env var"),
    # Logs
    (r"\.log$", "log", "Log file", None),
    (r"Library/Logs", "log", "Application logs", None),
    # Dev
    (r"node_modules/", "dev", "Node.js dependencies", "Run npm install to recreate"),
    (r"__pycache__/", "dev", "Python bytecode cache", "Regenerates automatically"),
    (r"\.pyc$", "dev", "Python compiled file", None),
    (r"\.venv/", "dev", "Python virtual env", "Recreate with python -m venv"),
    (r"\.idea/", "dev", "JetBrains IDE cache", None),
    (r"\.vs/", "dev", "Visual Studio cache", None),
    (r"/(build|dist|out)/(debug|release|bin|obj|classes)/", "dev", "Build output", "Run build to recreate"),
    (r"/projects?/.*/build/", "dev", "Project build output", "Run build to recreate"),
    (r"target/debug", "dev", "Rust debug build", "cargo build recreates"),
    (r"target/release", "dev", "Rust release build", "cargo build --release recreates"),
    (r"\.git/objects/", "dev", "Git objects", "Run git gc to optimize"),
    # System / local
    (r"\.DS_Store", "system", "macOS folder settings", None),
    (r"Library/Application Support/.*/Cache", "system", "App support cache", None),
    (r"Library/Safari", "browser", "Safari data", None),
    (r"Library/Caches/CloudKit", "system", "CloudKit cache", None),
    # Trash
    (r"\.Trash/", "recycle", "Trash", "Empty Trash in Finder"),
    # Downloads
    (r"Downloads/.*\.(dmg|pkg|zip|tar\.gz|iso)$", "download", "Downloaded installer/archive", None),
    # Duplicates
    (r"\s*\(\d+\)\.(jpg|png|mp4|mov)$", "duplicate", "Possible duplicate (numbered)", None),
    (r"\s*-?\s*copy\.(jpg|png|mp4|mov)$", "duplicate", "Possible duplicate (copy)", None),
]

SAFETY_LEVELS = {
    "temp": "safe",
    "cache": "safe",
    "log": "check",
    "backup": "check",
    "dev": "safe",
    "browser": "safe",
    "system": "check",
    "recycle": "check",
    "download": "check",
    "duplicate": "check",
}

# Pre-compile patterns for better performance
CLEANABLE_PATTERNS_COMPILED = [
    (re.compile(pattern), category, reason, hint)
    for pattern, category, reason, hint in CLEANABLE_PATTERNS
]


def parse_size(size_str: str) -> int:
    try:
        return int(size_str.strip().replace(",", "").replace(" ", "") or 0)
    except (ValueError, TypeError):
        return 0


def parse_human_size(value: str) -> int:
    """'500MB', '1.5 GB', '2048' → bytes."""
    m = re.match(r"^\s*([\d.]+)\s*([KMGT]?B?)\s*$", value.upper())
    if not m:
        return parse_size(value)
    mult = {"": 1, "B": 1, "K": 1024, "KB": 1024, "M": 1024**2, "MB": 1024**2,
            "G": 1024**3, "GB": 1024**3, "T": 1024**4, "TB": 1024**4}[m.group(2)]
    return int(float(m.group(1)) * mult)


def format_size(size_bytes: int) -> str:
    size_bytes = abs(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_path_depth(path: str) -> int:
    """Depth = number of path segments (POSIX)."""
    p = path.strip("/")
    if not p:
        return 0
    return len(p.split("/"))


def read_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Read scan_disk.py CSV. Header: path,size,allocated,modified,is_dir,files_count,folders_count."""
    files = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip().lower(): v for k, v in row.items()} if row else {}
            try:
                path = (row.get("path") or "").strip()
                if not path:
                    continue
                size = parse_size(row.get("size") or "0")
                allocated = parse_size(row.get("allocated") or "0")
                modified = (row.get("modified") or "").strip()
                is_dir = (row.get("is_dir") or "0").strip() in ("1", "true", "yes")
                files_count = int(row.get("files_count") or 0) if row.get("files_count") else 0
                folders_count = int(row.get("folders_count") or 0) if row.get("folders_count") else 0
                depth = get_path_depth(path)
                name = path.rstrip("/").split("/")[-1] if path else ""
                ext = Path(path).suffix.lower() if not is_dir else ""
                # All accounting uses real on-disk size; logical size is kept to spot
                # cloud-only placeholders (logical > 0, nothing allocated)
                entry = {
                    "path": path,
                    "size": allocated if "allocated" in row else size,
                    "logical": size,
                    "allocated": allocated,
                    "modified": modified,
                    "is_dir": is_dir,
                    "files_count": files_count,
                    "folders_count": folders_count,
                    "depth": depth,
                    "name": name,
                    "ext": ext,
                }
                files.append(entry)
            except (ValueError, TypeError):
                continue
    # Recompute folder sizes from their files' on-disk sizes (older scans summed logical sizes)
    dir_sizes = defaultdict(int)
    for f in files:
        if not f["is_dir"]:
            parts = f["path"].strip("/").split("/")
            for i in range(1, len(parts)):
                dir_sizes["/" + "/".join(parts[:i])] += f["size"]
    for f in files:
        if f["is_dir"]:
            f["size"] = dir_sizes.get(f["path"].rstrip("/"), 0)
    return files


def cmd_summary(files: List[Dict]) -> Dict:
    total_size = sum(f["size"] for f in files if not f["is_dir"])
    total_files = sum(1 for f in files if not f["is_dir"])
    total_dirs = sum(1 for f in files if f["is_dir"])
    by_ext = defaultdict(lambda: {"count": 0, "size": 0})
    for f in files:
        if not f["is_dir"] and f["ext"]:
            by_ext[f["ext"]]["count"] += 1
            by_ext[f["ext"]]["size"] += f["size"]
    top_extensions = sorted(by_ext.items(), key=lambda x: x[1]["size"], reverse=True)[:10]
    cloud = [f for f in files if not f["is_dir"] and f["logical"] > 0 and f["allocated"] == 0]
    result = {
        "cloud_only_bytes": sum(f["logical"] for f in cloud),
        "cloud_only_files": len(cloud),
        "total_size": format_size(total_size),
        "total_size_bytes": total_size,
        "total_files": total_files,
        "total_directories": total_dirs,
        "top_extensions": [
            {"ext": ext, "count": data["count"], "size": format_size(data["size"]), "size_bytes": data["size"]}
            for ext, data in top_extensions
        ],
    }
    emit("summary", result)
    return result


def cmd_largest(files: List[Dict], limit: int = 20) -> List[Dict]:
    file_only = [f for f in files if not f["is_dir"]]
    sorted_files = sorted(file_only, key=lambda x: x["size"], reverse=True)[:limit]
    result = [
        {"path": f["path"], "size": format_size(f["size"]), "size_bytes": f["size"]}
        for f in sorted_files
    ]
    emit("largest", result)
    return result


def cmd_by_type(files: List[Dict], limit: int = 30) -> List[Dict]:
    by_ext = defaultdict(lambda: {"count": 0, "size": 0})
    for f in files:
        if not f["is_dir"]:
            ext = f["ext"] if f["ext"] else "(no extension)"
            by_ext[ext]["count"] += 1
            by_ext[ext]["size"] += f["size"]
    sorted_types = sorted(by_ext.items(), key=lambda x: x[1]["size"], reverse=True)[:limit]
    result = [
        {
            "extension": ext,
            "count": data["count"],
            "size": format_size(data["size"]),
            "size_bytes": data["size"],
        }
        for ext, data in sorted_types
    ]
    emit("by-type", result)
    return result


def cmd_top_folders(files: List[Dict], max_depth: int = 2, limit: int = 10) -> Dict:
    # Find minimum depth (scan root depth) to calculate relative depths
    min_depth = min((f["depth"] for f in files if f["is_dir"]), default=0)

    by_rel_depth = defaultdict(list)
    for f in files:
        if f["is_dir"]:
            rel_depth = f["depth"] - min_depth
            if rel_depth > 0:  # Exclude the root itself (rel_depth=0)
                by_rel_depth[rel_depth].append(f)

    result = {"depths": {}, "scan_root_depth": min_depth}
    for rel_depth in range(1, max_depth + 1):
        if rel_depth in by_rel_depth:
            sorted_dirs = sorted(by_rel_depth[rel_depth], key=lambda x: x["size"], reverse=True)[:limit]
            result["depths"][rel_depth] = [
                {
                    "path": d["path"],
                    "size": format_size(d["size"]),
                    "size_bytes": d["size"],
                    "files_count": d.get("files_count", 0),
                    "folders_count": d.get("folders_count", 0),
                }
                for d in sorted_dirs
            ]
    emit("top-folders", result)
    return result


def cmd_folder(files: List[Dict], target_path: str, depth: int = 1) -> Dict:
    prefix = target_path.rstrip("/")
    target = prefix + "/"
    target_depth = get_path_depth(prefix)
    seen_paths = set()
    children = []
    for f in files:
        p = f["path"].rstrip("/")
        if p == prefix:
            continue
        if not (p + "/").startswith(target):
            continue
        # Deduplicate by path
        if p in seen_paths:
            continue
        seen_paths.add(p)
        rel_depth = f["depth"] - target_depth
        if rel_depth < 1 or rel_depth > depth:
            continue
        if rel_depth < depth and not f["is_dir"]:
            continue
        children.append({
            "path": f["path"],
            "name": f["name"],
            "size": format_size(f["size"]),
            "size_bytes": f["size"],
            "is_dir": f["is_dir"],
            "depth": rel_depth,
            "files_count": f.get("files_count", 0),
            "folders_count": f.get("folders_count", 0),
        })
    children = sorted(children, key=lambda x: x["size_bytes"], reverse=True)[:50]
    result = {
        "path": target_path.rstrip("/"),
        "depth": depth,
        "directories": [c for c in children if c["is_dir"]][:30],
        "files": [c for c in children if not c["is_dir"]][:20],
        "total_items": len(children),
    }
    emit("folder", result)
    return result


def cmd_cleanable(files: List[Dict]) -> Dict:
    cleanable = defaultdict(
        lambda: {"files": [], "total_size": 0, "reason": "", "migration_hints": set(), "safety": "safe"}
    )
    for f in files:
        if f["is_dir"]:
            continue
        path_lower = f["path"].lower()
        for pattern_re, category, reason, migration_hint in CLEANABLE_PATTERNS_COMPILED:
            if pattern_re.search(path_lower):
                cleanable[category]["files"].append({
                    "path": f["path"],
                    "size": format_size(f["size"]),
                    "size_bytes": f["size"],
                })
                cleanable[category]["total_size"] += f["size"]
                cleanable[category]["reason"] = reason
                cleanable[category]["safety"] = SAFETY_LEVELS.get(category, "check")
                if migration_hint:
                    cleanable[category]["migration_hints"].add(migration_hint)
                break
    for category in cleanable:
        # Save actual file count before truncating
        cleanable[category]["actual_file_count"] = len(cleanable[category]["files"])
        cleanable[category]["files"] = sorted(
            cleanable[category]["files"], key=lambda x: x["size_bytes"], reverse=True
        )[:50]
    result = {
        "categories": {
            cat: {
                "reason": data["reason"],
                "safety": data["safety"],
                "total_size": format_size(data["total_size"]),
                "total_size_bytes": data["total_size"],
                "file_count": data["actual_file_count"],
                "migration_hints": list(data["migration_hints"]) if data["migration_hints"] else None,
                "sample_files": data["files"][:10],
            }
            for cat, data in sorted(
                cleanable.items(), key=lambda x: x[1]["total_size"], reverse=True
            )
        },
        "by_safety": {"safe": [], "check": [], "admin": []},
        "total_cleanable_size": format_size(sum(d["total_size"] for d in cleanable.values())),
        "total_cleanable_bytes": sum(d["total_size"] for d in cleanable.values()),
    }
    for cat, data in cleanable.items():
        safety = data["safety"]
        result["by_safety"].setdefault(safety, []).append({
            "category": cat,
            "size": format_size(data["total_size"]),
            "size_bytes": data["total_size"],
        })
    for safety in result["by_safety"]:
        result["by_safety"][safety] = sorted(
            result["by_safety"][safety], key=lambda x: x["size_bytes"], reverse=True
        )
    emit("cleanable", result)
    return result


def cmd_search(files: List[Dict], pattern: str) -> List[Dict]:
    # Escape special regex chars, then convert glob wildcards
    escaped = re.escape(pattern)
    regex = escaped.replace(r"\*", ".*").replace(r"\?", ".")
    matches = []
    for f in files:
        if re.search(regex, f["name"]):
            matches.append({
                "path": f["path"],
                "size": format_size(f["size"]),
                "size_bytes": f["size"],
                "is_dir": f["is_dir"],
            })
    matches = sorted(matches, key=lambda x: x["size_bytes"], reverse=True)[:100]
    result = {"pattern": pattern, "matches": matches, "count": len(matches)}
    emit("search", result)
    return result


def cmd_filter(files: List[Dict], conditions: str) -> List[Dict]:
    def parse_condition(cond: str) -> Tuple[str, str, str]:
        for op in [">=", "<=", ">", "<", "=", "~"]:
            if op in cond:
                parts = cond.split(op, 1)
                return parts[0].strip(), op, parts[1].strip()
        return cond, "=", "true"

    def matches_condition(f: Dict, field: str, op: str, value: str) -> bool:
        if field == "size":
            cmp_size = parse_human_size(value)
            if op == ">": return f["size"] > cmp_size
            if op == ">=": return f["size"] >= cmp_size
            if op == "<": return f["size"] < cmp_size
            if op == "<=": return f["size"] <= cmp_size
            if op == "=": return f["size"] == cmp_size
        elif field == "ext":
            cmp_ext = value.lower() if value.startswith(".") else "." + value.lower()
            return (f["ext"] or "").lower() == cmp_ext
        elif field == "path":
            if op == "~":
                return value.lower() in f["path"].lower()
            return f["path"].lower() == value.lower()
        elif field == "name":
            if op == "~":
                return value.lower() in (f["name"] or "").lower()
            return (f["name"] or "").lower() == value.lower()
        elif field == "depth":
            cmp_depth = int(value)
            if op == ">": return f.get("depth", 0) > cmp_depth
            if op == ">=": return f.get("depth", 0) >= cmp_depth
            if op == "<": return f.get("depth", 0) < cmp_depth
            if op == "<=": return f.get("depth", 0) <= cmp_depth
            if op == "=": return f.get("depth", 0) == cmp_depth
        return True

    cond_list = [parse_condition(c.strip()) for c in conditions.split(",")]
    matches = []
    for f in files:
        if f["is_dir"]:
            continue
        if all(matches_condition(f, field, op, val) for field, op, val in cond_list):
            matches.append({
                "path": f["path"],
                "size": format_size(f["size"]),
                "size_bytes": f["size"],
            })
    matches = sorted(matches, key=lambda x: x["size_bytes"], reverse=True)[:100]
    result = {"conditions": conditions, "matches": matches, "count": len(matches)}
    emit("filter", result)
    return result


def cmd_dashboard(files: List[Dict], limit: int = 8) -> None:
    """One-screen overview: disk gauge, folders, types, cleanable, largest files."""
    global MODE
    MODE = "silent"
    dirs = [f for f in files if f["is_dir"]]
    root = min(dirs, key=lambda f: f["depth"])["path"] if dirs else "/"
    summary = cmd_summary(files)
    folders = cmd_top_folders(files, 1, limit)
    cleanable = cmd_cleanable(files)
    largest = cmd_largest(files, limit)
    _, tree = build_tree(files)
    print(viz.join(viz.render_dashboard(root, summary, folders, cleanable, largest, tree)))


def cmd_plan(files: List[Dict], plan_src: str) -> None:
    """Visualize a cleanup proposal: actions, cumulative freed space, disk before → after.

    plan_src: JSON file path or "-" for stdin. Items:
      {"label": "...", "safety": "safe|check|admin", "paths": ["~/.cache", ...]}  # size from CSV
      {"label": "...", "safety": "check", "bytes": 25000000000}                   # size measured elsewhere
    """
    raw = sys.stdin.read() if plan_src == "-" else Path(plan_src).read_text()
    items = json.loads(raw)
    file_rows = [f for f in files if not f["is_dir"]]
    for it in items:
        if "bytes" in it:
            continue
        prefixes = [str(Path(p).expanduser()).rstrip("/") for p in it.get("paths", [])]
        it["bytes"] = sum(
            f["size"] for f in file_rows
            if any(f["path"] == p or f["path"].startswith(p + "/") for p in prefixes)
        )
    print(viz.join(viz.render_plan(items, FREE_SPACE_PATH)))


def build_tree(files: List[Dict], top: int = 9, kids: int = 6) -> Tuple[str, List[Dict]]:
    """Two-level size tree relative to the scan root for the treemap."""
    dirs = [f for f in files if f["is_dir"]]
    root = min(dirs, key=lambda f: f["depth"])["path"].rstrip("/") if dirs else ""
    agg = defaultdict(lambda: {"bytes": 0, "children": defaultdict(int)})
    for f in files:
        if f["is_dir"] or not f["path"].startswith(root + "/"):
            continue
        parts = f["path"][len(root) + 1:].split("/")
        l1 = parts[0] if len(parts) > 1 else viz.t("files_node")
        l2 = parts[1] if len(parts) > 2 else viz.t("files_node")
        agg[l1]["bytes"] += f["size"]
        agg[l1]["children"][l2] += f["size"]

    def bucket(pairs, limit, label):
        pairs = sorted(pairs, key=lambda p: p[1], reverse=True)
        head, rest = pairs[:limit], pairs[limit:]
        out = [{"label": k, "bytes": v} for k, v in head if v > 0]
        if sum(v for _, v in rest) > 0:
            out.append({"label": f"{label} ({len(rest)})", "bytes": sum(v for _, v in rest), "other": True})
        return out

    tree = bucket([(k, v["bytes"]) for k, v in agg.items()], top, viz.t("other"))
    for t in tree:
        if not t.get("other"):
            t["children"] = bucket(agg[t["label"]]["children"].items(), kids, viz.t("more"))
    return root, tree


def cmd_treemap(files: List[Dict], height: int = 24) -> None:
    root, tree = build_tree(files)
    print(viz.join(viz.render_treemap(tree, root, viz.WIDTH - 1, height)))


def disk_snapshot(csv_path: str) -> Dict:
    """Disk usage saved by scan_disk.py next to the CSV, or None for older scans."""
    side = Path(csv_path + ".disk.json")
    return json.loads(side.read_text()) if side.exists() else None


def folder_sizes(files: List[Dict], depth: int) -> Dict[str, int]:
    """On-disk bytes per folder `depth` levels below the scan root."""
    dirs = [f for f in files if f["is_dir"]]
    root = min(dirs, key=lambda f: f["depth"])["path"].rstrip("/") if dirs else ""
    out = defaultdict(int)
    for f in files:
        if f["is_dir"] or not f["path"].startswith(root + "/"):
            continue
        parts = f["path"][len(root) + 1:].split("/")[:-1][:depth]
        out["/".join(parts) or viz.t("files_node")] += f["size"]
    return out


def cmd_compare(after_csv: str, after: List[Dict], before_csv: str,
                depth: int = 2, limit: int = 12) -> None:
    """Visualize a finished cleanup: disk before → after and what changed per folder.

    Both CSVs must come from scans of the same root (before and after cleanup).
    """
    if not Path(before_csv).exists():
        print(f"Error: CSV file not found: {before_csv}", file=sys.stderr)
        sys.exit(1)
    before = read_csv(before_csv)
    b_sizes, a_sizes = folder_sizes(before, depth), folder_sizes(after, depth)
    scan_delta = sum(b_sizes.values()) - sum(a_sizes.values())

    snap_a = disk_snapshot(after_csv)
    if not snap_a:
        import shutil
        du = shutil.disk_usage(FREE_SPACE_PATH)
        snap_a = {"total": du.total, "used": du.used, "free": du.free}
    snap_b = disk_snapshot(before_csv)
    estimated = snap_b is None
    if estimated:
        snap_b = {"total": snap_a["total"], "used": snap_a["used"] + scan_delta,
                  "free": snap_a["free"] - scan_delta}

    changes = [{"label": k, "before": b_sizes.get(k, 0), "after": a_sizes.get(k, 0)}
               for k in set(b_sizes) | set(a_sizes)]
    changes = [x for x in changes if abs(x["after"] - x["before"]) >= 1024 * 1024]
    changes.sort(key=lambda x: abs(x["after"] - x["before"]), reverse=True)
    print(viz.join(viz.render_compare(snap_b, snap_a, changes[:limit], depth, estimated)))


def get_option(name: str, default: int) -> int:
    if name in sys.argv:
        idx = sys.argv.index(name)
        if idx + 1 < len(sys.argv):
            try:
                return int(sys.argv[idx + 1])
            except ValueError:
                pass
    return default


def main():
    viz.USE_COLOR = "--color" in sys.argv
    viz.CHAT = "--chat-color" in sys.argv
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        viz.LANG = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "en"
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    csv_path = sys.argv[1]
    command = sys.argv[2].lower()
    if not Path(csv_path).exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    files = read_csv(csv_path)
    if command == "dashboard":
        cmd_dashboard(files, get_option("--limit", 8))
    elif command == "treemap":
        cmd_treemap(files, get_option("--height", 24))
    elif command == "plan":
        if len(sys.argv) < 4:
            print("Usage: analyze_disk.py <csv> plan <plan.json|->", file=sys.stderr)
            sys.exit(1)
        cmd_plan(files, sys.argv[3])
    elif command == "compare":
        if len(sys.argv) < 4:
            print("Usage: analyze_disk.py <after.csv> compare <before.csv> [--depth N] [--limit N]",
                  file=sys.stderr)
            sys.exit(1)
        cmd_compare(csv_path, files, sys.argv[3], get_option("--depth", 2), get_option("--limit", 12))
    elif command == "summary":
        cmd_summary(files)
    elif command == "largest":
        cmd_largest(files, get_option("--limit", 20))
    elif command == "by-type":
        cmd_by_type(files, get_option("--limit", 30))
    elif command == "top-folders":
        cmd_top_folders(
            files,
            get_option("--depth", 2),
            get_option("--limit", 10),
        )
    elif command == "folder":
        if len(sys.argv) < 4:
            print("Usage: analyze_disk.py <csv> folder <path> [--depth N]", file=sys.stderr)
            sys.exit(1)
        cmd_folder(files, sys.argv[3], get_option("--depth", 1))
    elif command == "cleanable":
        cmd_cleanable(files)
    elif command == "search":
        if len(sys.argv) < 4:
            print("Usage: analyze_disk.py <csv> search <pattern>", file=sys.stderr)
            sys.exit(1)
        cmd_search(files, sys.argv[3])
    elif command == "filter":
        if len(sys.argv) < 4:
            print("Usage: analyze_disk.py <csv> filter <conditions>", file=sys.stderr)
            sys.exit(1)
        cmd_filter(files, sys.argv[3])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Commands: dashboard, treemap, plan, compare, summary, largest, by-type, top-folders, folder, cleanable, search, filter")
        sys.exit(1)


if __name__ == "__main__":
    main()
