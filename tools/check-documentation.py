"""Check local links in canonical and rebuilt learning pages. No network calls."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src") and value:
                self.links.append(value)


def main():
    errors = []
    checked = 0
    for directory in (ROOT / "learnings", ROOT / "mockups/procurement-ui-prototype/public/learnings"):
        if not directory.is_dir():
            errors.append(f"Missing learning directory: {directory.relative_to(ROOT)}")
            continue
        for path in directory.rglob("*.html"):
            links = Links()
            links.feed(path.read_text(encoding="utf-8"))
            checked += 1
            for link in links.links:
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (path.parent / unquote(parsed.path)).resolve()
                if not target.is_file():
                    errors.append(f"{path.relative_to(ROOT)}: missing local target {link}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Learning links passed: {checked} HTML files")


if __name__ == "__main__":
    main()
