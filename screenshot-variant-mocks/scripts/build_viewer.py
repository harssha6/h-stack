#!/usr/bin/env python3
"""Build the interactive variant viewer from a manifest.

  build_viewer.py manifest.json [--out viewer.html] [--inline]

Without --inline the HTML references images by path relative to the output file (light, for the
artifact folder). With --t3 images use absolute paths, which T3's html_preview/html_render inline, and the page adopts
T3 theme variables (render with html_render path=..., height from html_preview). With --inline every image is embedded as a data URI: one self-contained file that
works in T3's html_preview and can be opened or shared anywhere without the folder.

manifest.json (paths relative to the manifest):
{
  "id": "android-byline", "title": "...", "subtitle": "...", "stamp": "PROPOSAL, not a decision · ...",
  "decision": "optional HTML banner, e.g. the chosen direction",
  "views": [{"key": "full", "label": "Full screen"}, {"key": "close", "label": "Close-up 1:1"}],
  "state_labels": {"photo": "With photo", "fallback": "No photo"},
  "state_groups": [{"label": "", "states": ["photo"]}, {"label": "No photo", "states": ["fallback"], "short": {"fallback": "Initials"}}],
  "embed_defaults": {"view": "close", "cols": 3, "state": "photo"},
  "variants": [{"id": "a", "tag": "optional short label", "name": "Plain name", "desc": "...",
                "states": {"photo": {"full": "web/a_full.jpg", "close": "web/a_close.jpg"}}}],
  "scores": {"judges": ["judge-a", "judge-b"],
             "criteria": [{"key": "person_cue", "label": "Person", "abbr": "Cue", "desc": "..."}],
             "by_variant": {"a": {"judge-a": {"person_cue": 3, "verdict": "..."}}},
             "note": "optional caveat"},
  "refs": [{"app": "VSCO", "pattern": "...", "image": "refs/01.jpg", "url": "https://mobbin.com/..."}]
}
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svmock as S

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer_template.html")

def walk_images(m, fn):
    for v in m.get("variants", []):
        for st in v.get("states", {}).values():
            for k in list(st): st[k] = fn(st[k])
    for r in m.get("refs", []):
        if r.get("image"): r["image"] = fn(r["image"])

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("manifest"); ap.add_argument("--out"); ap.add_argument("--inline", action="store_true")
    ap.add_argument("--t3", action="store_true", help="T3 html_render version: absolute image paths (T3 inlines them), theme variables, no page background")
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.manifest)); m = json.load(open(a.manifest))
    out = os.path.abspath(a.out or os.path.join(base, "viewer_inline.html" if a.inline else "viewer_t3.html" if a.t3 else "viewer.html"))
    if a.t3:
        m["embed"] = True
        m.setdefault("defaults", {}).update(m.get("embed_defaults", {}))
    missing = []
    def fix(p):
        full = p if os.path.isabs(p) else os.path.join(base, p)
        if not os.path.exists(full): missing.append(p); return p
        if a.inline: return S.data_uri(full)
        return full if a.t3 else os.path.relpath(full, os.path.dirname(out))
    walk_images(m, fix)
    if missing: print("MISSING images:", *missing, sep="\n  ")
    html = open(TEMPLATE).read().replace("/*__MANIFEST__*/{}", json.dumps(m).replace("</", "<\\/"))
    open(out, "w").write(html)
    print(out, f"{os.path.getsize(out) / 1e6:.1f} MB")

if __name__ == "__main__":
    main()
