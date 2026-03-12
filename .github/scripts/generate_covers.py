#!/usr/bin/env python3
"""
generate_covers.py
Generates 1200x630 branded cover images for author submissions that have no og:image.
Run from the repository root.
"""

import os
import re
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

COVER_W = 1200
COVER_H = 630

BG      = (26, 24, 21)
BORDER  = (46, 43, 39)
ACCENT  = (139, 101, 53)
TEXT    = (240, 236, 232)
MUTED   = (107, 98, 88)

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def extract_meta(html, name):
    m = re.search(rf'<meta\s+name=["\']{{0}}["\']\s+content=["\']([^"\']+)["\']'.format(name), html, re.IGNORECASE)
    if not m:
        m = re.search(rf'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']{{0}}["\']'.format(name), html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def extract_title(html):
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def extract_og_image(html):
    m = re.search(r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def load_fonts():
    try:
        return {
            "small":  ImageFont.truetype(FONT_REG,  22),
            "title":  ImageFont.truetype(FONT_BOLD, 64),
            "desc":   ImageFont.truetype(FONT_REG,  28),
            "author": ImageFont.truetype(FONT_REG,  24),
        }
    except Exception:
        default = ImageFont.load_default()
        return {"small": default, "title": default, "desc": default, "author": default}


def make_cover(slug, title, author, description, out_path):
    img = Image.new("RGB", (COVER_W, COVER_H), BG)
    d   = ImageDraw.Draw(img)
    f   = load_fonts()

    # Outer border
    d.rectangle([0, 0, COVER_W - 1, COVER_H - 1], outline=BORDER, width=2)

    # Gold accent bar
    d.rectangle([48, 52, 180, 55], fill=ACCENT)

    # Brand label
    d.text((48, 66), "✦ claudeslides", font=f["small"], fill=MUTED)

    # Title (max 3 lines, ~26 chars wide)
    y = 170
    for line in textwrap.wrap(title, width=26)[:3]:
        d.text((48, y), line, font=f["title"], fill=TEXT)
        y += 80

    # Description (max 2 lines)
    if description:
        y += 12
        for line in textwrap.wrap(description, width=58)[:2]:
            d.text((48, y), line, font=f["desc"], fill=MUTED)
            y += 38

    # Bottom: author name left, ✦ right
    d.text((48, COVER_H - 68), author, font=f["author"], fill=ACCENT)
    d.text((COVER_W - 72, COVER_H - 68), "✦", font=f["author"], fill=MUTED)

    img.save(out_path, "JPEG", quality=88, optimize=True)
    print(f"  ✓ {out_path}")


def main():
    repo_root  = Path(__file__).resolve().parent.parent.parent
    author_dir = repo_root / "author"
    covers_dir = repo_root / "covers"
    covers_dir.mkdir(exist_ok=True)

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

            if extract_og_image(html):
                print(f"  — {author_slug}/{slide_slug}: has og:image, skipping")
                continue

            out_dir = covers_dir / author_slug
            out_dir.mkdir(exist_ok=True)

            make_cover(
                slug=slide_slug,
                title=extract_title(html) or slide_slug,
                author=extract_meta(html, "author") or author_slug,
                description=extract_meta(html, "description") or "",
                out_path=str(out_dir / f"{slide_slug}.jpg"),
            )

    print("Done.")


if __name__ == "__main__":
    main()
