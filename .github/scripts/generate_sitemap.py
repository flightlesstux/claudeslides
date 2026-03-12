#!/usr/bin/env python3
"""
generate_sitemap.py
Generates sitemap.xml from all pages in the repo.
Run from the repository root.
"""

from pathlib import Path
from datetime import datetime, timezone

BASE_URL = "https://claudeslides.com"


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    today = datetime.now(timezone.utc).date().isoformat()

    urls = [
        {"loc": f"{BASE_URL}/",           "changefreq": "daily",   "priority": "1.0", "lastmod": today},
        {"loc": f"{BASE_URL}/contribute/", "changefreq": "monthly", "priority": "0.8", "lastmod": today},
    ]

    author_dir = repo_root / "author"
    if author_dir.exists():
        for author_subdir in sorted(author_dir.iterdir()):
            if not author_subdir.is_dir():
                continue
            for slide_dir in sorted(author_subdir.iterdir()):
                if slide_dir.is_dir() and (slide_dir / "index.html").exists():
                    urls.append({
                        "loc": f"{BASE_URL}/author/{author_subdir.name}/{slide_dir.name}/",
                        "changefreq": "yearly",
                        "priority": "0.6",
                        "lastmod": today,
                    })

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{u['loc']}</loc>")
        lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        lines.append(f"    <priority>{u['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")

    out = repo_root / "sitemap.xml"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written {len(urls)} URLs to sitemap.xml")


if __name__ == "__main__":
    main()
