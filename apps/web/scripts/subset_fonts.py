"""Build local reading fonts from upstream TTFs; requires fontTools (build-time only).

Usage: python apps/web/scripts/subset_fonts.py regular.ttf semibold.ttf
Only the checked-in UI and course copy is inspected. Uncovered dynamic glyphs
use the CSS fallback family; no learner data is sent to a font service.
"""
from pathlib import Path
import sys

from fontTools import subset


def main() -> None:
    web = Path(__file__).resolve().parents[1]
    repo = web.parents[1]
    characters = set(range(0x20, 0x7F)) | set(range(0x2000, 0x2070)) | set(range(0x3000, 0x3040))
    for root in (web / "src", repo / "course_packs"):
        for path in root.rglob("*"):
            if path.suffix in {".vue", ".ts", ".md", ".json", ".yaml", ".yml"}:
                characters.update(map(ord, path.read_text(encoding="utf-8")))
    destination = web / "src" / "assets" / "fonts"
    destination.mkdir(parents=True, exist_ok=True)
    for weight, source in zip((400, 600), sys.argv[1:], strict=True):
        options = subset.Options()
        options.flavor = "woff"
        options.hinting = False
        font = subset.load_font(source, options)
        processor = subset.Subsetter(options=options)
        processor.populate(unicodes=characters)
        processor.subset(font)
        output = destination / f"noto-sans-sc-{weight}.woff"
        subset.save_font(font, output, options)
        print(f"{output.name}: {output.stat().st_size:,} bytes, {len(font.getBestCmap()):,} glyphs")


if __name__ == "__main__":
    main()
