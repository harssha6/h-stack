#!/usr/bin/env python3
"""Run an offline smoke check: python3 synthetic.py /tmp/variant-example.

Writes two synthetic screenshots, a comparison board, a rubric and three viewers.
No product assets, API credentials or network access are needed.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import svmock as S


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path)
    ap.add_argument("--font", default="DejaVuSans.ttf", help="Path or installed name of a TrueType/OpenType font")
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = Image.new("RGBA", (240, 360), (20, 20, 20, 255))
    ImageDraw.Draw(source).rectangle((20, 20, 219, 239), fill=(80, 100, 140))
    font = ImageFont.truetype(args.font, 16)
    ImageDraw.Draw(source).text((20, 260), "Example label", font=font, fill=(180, 180, 180))
    source.save(out / "source.png")
    control = S.load(out / "source.png")
    variant = control.copy()
    S.erase(variant, (15, 250, 230, 300), (20, 20, 20))
    variant.alpha_composite(S.disc(16, (180, 180, 180)), (20, 262))
    ImageDraw.Draw(variant).text((44, 260), S.fit("Example label", font, 175), font=font, fill=(180, 180, 180))
    assert S.segments(control, 100) == [(20, 220)]
    assert S.text_box(control, (15, 250, 230, 300)) is not None
    assert S.bands(control, 20, 220, 0, 250)
    assert control.crop((0, 0, 240, 250)).tobytes() == variant.crop((0, 0, 240, 250)).tobytes()
    variants = []
    for key, name, im in (("a", "Control", control), ("b", "Icon label", variant)):
        im.save(out / f"{key}.png")
        im.crop((0, 245, 240, 310)).save(out / f"{key}_close.png")
        views = {"full": f"{key}.png", "close": f"{key}_close.png"}
        variants.append({"id": key, "name": name, "states": {"filled": views, "fallback": views}})
    S.board([(control, "A", "Control"), (variant, "B", "Icon label")], "Synthetic label mocks",
            "PROPOSAL · drawn shapes only", out / "board.png", font.path, font.path)
    manifest = {"id": "synthetic-label", "title": "Synthetic label mocks", "stamp": "PROPOSAL · synthetic data",
        "views": [{"key": "close", "label": "Close-up"}, {"key": "full", "label": "Full screen"}],
        "state_labels": {"filled": "With data", "fallback": "Fallback"}, "variants": variants,
        "scores": {"judges": ["judge-a", "judge-b"], "criteria": [{"key": "legibility", "label": "Legibility"}],
            "by_variant": {k: {m: {"legibility": 7, "verdict": "Fixture only", "biggest_risk": "Not a real judgment"}
                for m in ("judge-a", "judge-b")} for k in ("a", "b")}, "note": "Synthetic fixture scores, not model judgments"}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    rubric = {"context": "Synthetic label: {desc}", "criteria": {"legibility": "Readable at actual width"},
              "items": {v["id"]: {"image": f'{v["id"]}.png', "desc": v["name"]} for v in variants}}
    (out / "rubric.json").write_text(json.dumps(rubric, indent=2))
    for flags in ([], ["--inline"], ["--t3"]):
        subprocess.run([sys.executable, str(SCRIPTS / "build_viewer.py"), str(out / "manifest.json"), *flags], check=True)
    import os
    subprocess.run([sys.executable, str(SCRIPTS / "judge_vision.py"), str(out / "rubric.json"), "--dry-run"],
                   env={**os.environ, "VISION_MODELS": '["judge-a", "judge-b"]'}, check=True)
    assert not (out / "scores.json").exists(), "Dry-run must not fabricate scores"
    print("PASS: compositing, measurements, board, three viewers and judge dry-run")


if __name__ == "__main__":
    main()
