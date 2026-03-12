#!/usr/bin/env python3
"""
moderate_content.py
Content safety scanner for claudeslides PR submissions.

Usage:
    python moderate_content.py author/some-slug/index.html

Exit codes:
    0 — passed
    1 — failed (harmful content detected)
    2 — error (could not read file)
"""

import re
import sys
import json
from pathlib import Path
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

class TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "head"}

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip += 1
        # Also collect alt / title / placeholder attribute text
        for name, value in attrs:
            if name.lower() in ("alt", "title", "placeholder", "aria-label") and value:
                self.text_parts.append(value)

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip == 0:
            self.text_parts.append(data)

    def get_text(self):
        return " ".join(self.text_parts)


def extract_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text().lower()


# ---------------------------------------------------------------------------
# Pattern lists  (keep these purposefully non-exhaustive and maintainable)
# ---------------------------------------------------------------------------

# Each entry: (category_label, [regex_patterns])
CHECKS = [
    ("hate_speech", [
        r"\bn[i!1]+gg[ae]r\b",
        r"\bch[i!1]+nk\b",
        r"\bsp[i!1]+c\b",
        r"\bk[i!1]+ke\b",
        r"\bf[a4]+gg?[o0]+t\b",
        r"\btr[a4]+nn[yi]\b",
        r"\bwhite\s+suprem",
        r"\bheil\s+hitler",
        r"\bgas\s+the\s+jews",
        r"\bkill\s+all\s+\w+s\b",
        r"\b(jews?|blacks?|muslims?|christians?)\s+(are|should)\s+(sub|inferior|evil|vermin)",
    ]),
    ("sexism", [
        r"\bwomen\s+(belong|should\s+be)\s+in\s+the\s+kitchen",
        r"\bfeminist[s]?\s+(are|is)\s+(evil|cancer|disease|plague)",
        r"\ball\s+women\s+(are|deserve)",
        r"\bwomen\s+are\s+(inferior|property|objects?)",
        r"\bslu+t\b",
        r"\bwh[o0]+re\b",
    ]),
    ("csam", [
        r"\bchild\s+porn",
        r"\bcp\s+link",
        r"\bloli\s+(hentai|porn|nude)",
        r"\bpedo(phile)?s?\b.*\b(love|support|ok|fine)\b",
        r"\b(underage|minor)\s+(nude|naked|sex|porn)",
        r"\bcsa\s+material",
    ]),
    ("harassment", [
        r"\bkys\b",  # kill yourself
        r"\bkill\s+your\s*self",
        r"\bi\s+will\s+(find|hunt|rape|kill)\s+you",
        r"\bdox(x?ing)?\b",
    ]),
    ("malicious_code", [
        r"<script[^>]*>.*?(eval\s*\(|document\.cookie|window\.location\s*=|fetch\s*\(\s*['\"]https?://(?!cdn\.|unpkg\.|jsdelivr\.))",
        r"javascript:\s*void\(0\)\s*;\s*eval",
        r"on(load|error|click)\s*=\s*['\"]eval\(",
    ]),
]


# ---------------------------------------------------------------------------
# Ollama integration (optional — skipped gracefully if not available)
# ---------------------------------------------------------------------------

def ollama_check(text: str) -> dict | None:
    """
    Ask a local Ollama model to classify content.
    Returns {"safe": bool, "reason": str} or None if Ollama unavailable.
    """
    try:
        import urllib.request
        snippet = text[:3000]  # keep prompt short
        payload = {
            "model": "llama3",
            "prompt": (
                "You are a content moderation assistant. "
                "Classify the following text as SAFE or UNSAFE. "
                "UNSAFE means it contains hate speech, sexism, child abuse material, "
                "harassment, or malicious intent. "
                "Reply ONLY with a JSON object: {\"safe\": true/false, \"reason\": \"...\"}.\n\n"
                f"TEXT:\n{snippet}"
            ),
            "stream": False,
        }
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            response_text = data.get("response", "")
            # Extract JSON from model response
            m = re.search(r'\{[^}]+\}', response_text)
            if m:
                return json.loads(m.group())
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: moderate_content.py <path/to/index.html>")
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(2)

    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"ERROR: Cannot read file: {e}")
        sys.exit(2)

    text = extract_text(html)
    findings = []

    # Pattern-based checks
    for category, patterns in CHECKS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                findings.append(f"[{category}] Pattern matched: `{pattern}`")
                break  # one finding per category is enough

    # Ollama check (best-effort)
    ollama_result = ollama_check(text)
    ollama_note = ""
    if ollama_result is not None:
        if not ollama_result.get("safe", True):
            findings.append(f"[ollama] {ollama_result.get('reason', 'Flagged as unsafe')}")
        ollama_note = f"\nOllama review: {'✅ safe' if ollama_result.get('safe') else '❌ unsafe'} — {ollama_result.get('reason', '')}"

    # Report
    if findings:
        print("## ❌ Content moderation FAILED\n")
        print(f"File: `{path}`\n")
        print("Issues found:\n")
        for f in findings:
            print(f"- {f}")
        if ollama_note:
            print(ollama_note)
        print(
            "\nPlease revise your submission to comply with the "
            "[contribution guidelines](CONTRIBUTING.md)."
        )
        sys.exit(1)
    else:
        print(f"✅ Content moderation passed for `{path}`{ollama_note}")
        sys.exit(0)


if __name__ == "__main__":
    main()
