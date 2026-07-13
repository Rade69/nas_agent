"""Filesystem folder/file search tool handler.

User-reported gap (2026-07-13, agent_reports/2026-07-13_filesystem-search-tool.md):
with no way to search the filesystem, Ricky's only option when asked "find
the thumbnails folder" was to blindly click/type through File Explorer —
each such click/type is a high-risk, confirmation-gated computer-use tool, so
a single "find X" request turned into a chain of fresh confirmation dialogs
the user experienced as an infinite loop.

Revision (same day): the first version walked each root depth-first
(`os.walk`), which could exhaust the whole time budget crawling one huge,
deep subtree (typically `AppData`, which sorts alphabetically before
`Desktop`/`Documents`/`Downloads`) before ever reaching the shallow folder
the user actually wanted — reported back as "the agent can't find anything."
Investigated using the real Windows Search index (ADODB /
Search.CollatorDataSource, the "use a proper library" suggestion) as a
faster alternative, but the provider isn't registered on this machine (a
common 32/64-bit COM registration gap) and can't be relied on. Fixed instead
by switching to breadth-first search across all roots at once (a single
queue seeded with data_dir + home + every fixed drive): shallow matches
anywhere are found before the walk descends deep into any one subtree,
regardless of alphabetical ordering or how large that subtree is.

Risk: low, no confirmation (see tool_catalog/phase11.py registration) — this
only returns folder/file NAMES and paths, never file contents.
"""
from __future__ import annotations

import os
import time
from collections import deque
from pathlib import Path
from typing import Any

MAX_RESULTS = 40
MAX_SECONDS = 10.0

# Directories that are either huge, OS-internal noise, or routinely
# access-denied — skipping them keeps the search fast and avoids burning the
# time budget on folders a user would never ask to find.
SKIP_DIR_NAMES = {
    "$recycle.bin",
    "system volume information",
    "winsxs",
    "installer",
    "node_modules",
    ".git",
}


def _drive_roots() -> list[Path]:
    if os.name != "nt":
        return []
    roots: list[Path] = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = Path(f"{letter}:\\")
        if drive.exists():
            roots.append(drive)
    return roots


def _search_roots(data_dir: Path) -> list[Path]:
    home = Path.home()
    ordered = [data_dir, home, *_drive_roots()]
    seen: set[Path] = set()
    roots: list[Path] = []
    for root in ordered:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        roots.append(resolved)
    return roots


def _bfs_search(roots: list[Path], query: str, target_type: str, deadline: float) -> tuple[list[dict[str, str]], bool]:
    """Breadth-first across ALL roots at once (one shared queue), not one
    root fully exhausted before the next. This is what makes shallow matches
    surface before the search ever goes deep into a large subtree — see the
    module docstring "Revision" note for why this replaced a per-root
    depth-first os.walk.

    `deadline` (an absolute time.monotonic() value, not a duration) is
    supplied by the caller rather than computed here so that a
    singular/plural retry pass (see make_handlers below) shares ONE combined
    time budget with the first pass instead of getting its own fresh
    MAX_SECONDS and doubling worst-case latency for a genuine "not found"."""
    results: list[dict[str, str]] = []
    visited: set[Path] = set()
    queue: deque[Path] = deque(roots)
    truncated = False

    while queue:
        if len(results) >= MAX_RESULTS or time.monotonic() > deadline:
            truncated = True
            break
        current = queue.popleft()
        try:
            resolved = current.resolve()
        except OSError:
            continue
        if resolved in visited:
            continue
        visited.add(resolved)
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue

        for entry in entries:
            # Real-world hardening: a directory walk over the whole system
            # WILL hit protected/unusual entries (other users' profiles,
            # reparse points, permission-denied files) — any single
            # DirEntry call here can raise OSError, and an uncaught one would
            # crash the entire search instead of just skipping that entry.
            try:
                if entry.is_symlink():
                    # Skip symlinks/junctions entirely — avoids classic
                    # Windows reparse-point loops (e.g. AppData's
                    # "Application Data" junction) and ambiguous
                    # file-vs-dir matching.
                    continue
                name_lower = entry.name.lower()
                is_dir = entry.is_dir()
            except OSError:
                continue
            if is_dir:
                if name_lower in SKIP_DIR_NAMES:
                    continue
                if target_type in ("folder", "any") and query in name_lower:
                    results.append({"name": entry.name, "path": entry.path})
                queue.append(Path(entry.path))
            elif target_type in ("file", "any") and query in name_lower:
                results.append({"name": entry.name, "path": entry.path})
            if len(results) >= MAX_RESULTS:
                break

    return results[:MAX_RESULTS], truncated


def make_handlers(data_dir: Path) -> dict[str, Any]:
    def filesystem_search(arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip().lower()
        if not query:
            raise ValueError("filesystem_search requires a non-empty 'query' string argument.")
        # Default "any" (not "folder"): real-world test against this app's own
        # data dir found the actual thumbnails are loose *files* directly in
        # data_dir (thumbnail-<id>.png), not inside a "thumbnails" subfolder —
        # a folder-only default would report "nothing found" for exactly the
        # request that motivated this tool. Most users asking to "find X"
        # don't distinguish file vs. folder; only narrow when they say so.
        target_type = str(arguments.get("type") or "any")
        if target_type not in ("folder", "file", "any"):
            target_type = "any"

        roots = _search_roots(data_dir)
        # One shared deadline for the whole call (including a possible
        # plural-fallback retry below) — a real full-drive pass measured
        # 5-9s on a modest dev machine, so two independent MAX_SECONDS
        # budgets could take a voice turn close to 20s for a genuine
        # "not found" query. Sharing one budget caps the worst case at
        # MAX_SECONDS total instead of doubling it.
        deadline = time.monotonic() + MAX_SECONDS
        results, truncated = _bfs_search(roots, query, target_type, deadline)
        # Simple English singular/plural fallback (e.g. a spoken "find the
        # thumbnails folder" naturally produces query="thumbnails", but the
        # files are named "thumbnail-<id>.png" — no plural "s"). Only retried
        # when the first pass genuinely finished with zero matches, not when
        # it was cut off by the time budget — retrying a truncated search
        # would just immediately truncate again for no benefit.
        if not results and not truncated and query.endswith("s") and len(query) > 1:
            results, truncated = _bfs_search(roots, query[:-1], target_type, deadline)

        summary = f"Found {len(results)} match(es) for '{query}'."
        if truncated:
            summary += " Search stopped early (too many results or took too long) — try a more specific name."
        lines = "\n".join(f"- {r['name']}  ({r['path']})" for r in results) or "(no matches)"
        return {
            "results": results,
            "truncated": truncated,
            "artifact": {
                "title": f"Filesystem search: {query}",
                "kind": "text",
                "content": f"{summary}\n\n{lines}",
            },
        }

    return {"filesystem_search": filesystem_search}
