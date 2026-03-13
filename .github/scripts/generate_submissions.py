#!/usr/bin/env python3
"""
generate_submissions.py
Scans author/*/index.html, extracts metadata, and writes submissions.json.
Run from the repository root.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone


def extract_meta(html: str, name: str) -> str:
    pattern = rf'<meta\s+name=["\']{{0}}["\']\s+content=["\']([^"\']+)["\']'.format(name)
    m = re.search(pattern, html, re.IGNORECASE)
    if not m:
        pattern = rf'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']{{0}}["\']'.format(name)
        m = re.search(pattern, html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def extract_title(html: str) -> str:
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def extract_og_image(html: str) -> str:
    m = re.search(
        r'<meta\s+(?:property=["\']og:image["\']\s+content|content=["\']([^"\']+)["\']\s+property=["\']og:image)["\']([^"\']*)["\']',
        html, re.IGNORECASE
    )
    if m:
        return (m.group(1) or m.group(2)).strip()
    # simpler fallback
    m = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def git_date(path: Path) -> str:
    """Return ISO date of last git commit touching this file, or today."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", str(path)],
            capture_output=True, text=True
        )
        date = result.stdout.strip()
        if date:
            return date[:10]
    except Exception:
        pass
    return datetime.now(timezone.utc).date().isoformat()


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    author_dir = repo_root / "author"

    submissions = []

    for author_subdir in sorted(author_dir.iterdir()):
        if not author_subdir.is_dir():
            continue
        for slide_dir in sorted(author_subdir.iterdir()):
            if not slide_dir.is_dir():
                continue
            html_file = slide_dir / "index.html"
            if not html_file.exists():
                continue

            html = html_file.read_text(encoding="utf-8", errors="replace")
            author_slug = author_subdir.name
            slide_slug  = slide_dir.name

            og_image   = extract_og_image(html)
            cover_file = slide_dir / "cover.jpg"
            cover_url  = og_image or (f"author/{author_slug}/{slide_slug}/cover.jpg" if cover_file.exists() else "")

            entry = {
                "author_slug": author_slug,
                "slug":        slide_slug,
                "url":         f"author/{author_slug}/{slide_slug}/",
                "title":       extract_title(html) or slide_slug,
                "author":      extract_meta(html, "author") or author_slug,
                "description": extract_meta(html, "description") or "",
                "og_image":    og_image,
                "cover_url":   cover_url,
                "date":        git_date(html_file),
            }
            submissions.append(entry)

    # Newest first
    submissions.sort(key=lambda x: x["date"], reverse=True)

    out = repo_root / "submissions.json"
    out.write_text(json.dumps(submissions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Written {len(submissions)} entries to submissions.json")


if __name__ == "__main__":
    main()
