#!/usr/bin/env python3
"""
inject_seo.py
Injects missing SEO meta tags into author submission pages.
Only adds what's missing — never overwrites or touches author content.
Run from the repository root.
"""

import re
from pathlib import Path

BASE_URL = "https://claudeslides.com"


def extract_meta(html, name):
    m = re.search(rf'<meta\s+name=["\']{{0}}["\']\s+content=["\']([^"\']+)["\']'.format(name), html, re.IGNORECASE)
    if not m:
        m = re.search(rf'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']{{0}}["\']'.format(name), html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def extract_title(html):
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def has_tag(html, pattern):
    return bool(re.search(pattern, html, re.IGNORECASE))


def inject_seo(html, author_slug, slide_slug):
    url         = f"{BASE_URL}/author/{author_slug}/{slide_slug}/"
    title       = extract_title(html) or slide_slug
    description = extract_meta(html, "description") or f"A Claude AI project by {author_slug}."

    tags = []

    if not has_tag(html, r'name=["\']robots["\']'):
        tags.append('<meta name="robots" content="index, follow">')

    if not has_tag(html, r'rel=["\']canonical["\']'):
        tags.append(f'<link rel="canonical" href="{url}">')

    if not has_tag(html, r'property=["\']og:type["\']'):
        tags.append('<meta property="og:type" content="article">')

    if not has_tag(html, r'property=["\']og:site_name["\']'):
        tags.append('<meta property="og:site_name" content="ClaudeSlides">')

    if not has_tag(html, r'property=["\']og:url["\']'):
        tags.append(f'<meta property="og:url" content="{url}">')

    if not has_tag(html, r'property=["\']og:title["\']'):
        tags.append(f'<meta property="og:title" content="{title}">')

    if not has_tag(html, r'property=["\']og:description["\']'):
        tags.append(f'<meta property="og:description" content="{description}">')

    cover_url = f"{BASE_URL}/author/{author_slug}/{slide_slug}/cover.jpg"
    if not has_tag(html, r'property=["\']og:image["\']'):
        tags.append(f'<meta property="og:image" content="{cover_url}">')
        tags.append('<meta property="og:image:width" content="1200">')
        tags.append('<meta property="og:image:height" content="630">')

    if not has_tag(html, r'name=["\']twitter:card["\']'):
        tags.append('<meta name="twitter:card" content="summary_large_image">')

    if not has_tag(html, r'name=["\']twitter:title["\']'):
        tags.append(f'<meta name="twitter:title" content="{title}">')

    if not has_tag(html, r'name=["\']twitter:description["\']'):
        tags.append(f'<meta name="twitter:description" content="{description}">')

    if not has_tag(html, r'name=["\']twitter:image["\']'):
        tags.append(f'<meta name="twitter:image" content="{cover_url}">')

    if not tags:
        return html, False

    block = "\n<!-- auto-seo: injected by ClaudeSlides CI -->\n" + "\n".join(tags) + "\n"
    new_html = re.sub(r'(</head>)', block + r'\1', html, count=1, flags=re.IGNORECASE)
    return new_html, True


def main():
    repo_root  = Path(__file__).resolve().parent.parent.parent
    author_dir = repo_root / "author"
    updated    = 0

    for author_subdir in sorted(author_dir.iterdir()):
        if not author_subdir.is_dir():
            continue
        for slide_dir in sorted(author_subdir.iterdir()):
            if not slide_dir.is_dir():
                continue
            html_file = slide_dir / "index.html"
            if not html_file.exists():
                continue

            html        = html_file.read_text(encoding="utf-8", errors="replace")
            author_slug = author_subdir.name
            slide_slug  = slide_dir.name

            new_html, changed = inject_seo(html, author_slug, slide_slug)
            if changed:
                html_file.write_text(new_html, encoding="utf-8")
                print(f"  ✓ {author_slug}/{slide_slug}: SEO injected")
                updated += 1
            else:
                print(f"  — {author_slug}/{slide_slug}: already complete")

    print(f"Done. {updated} file(s) updated.")


if __name__ == "__main__":
    main()
