#!/usr/bin/env python3
"""Edit a screen recording into a clean-then-breakdown 1080p demo.

  demo_video.py cfr SOURCE OUT [--fps 60]              constant-frame-rate copy (do this first)
  demo_video.py frames SOURCE OUTDIR --at 12 25.5 [--crop x,y,w,h]
  demo_video.py plan SPEC.json                         print the timing table without rendering
  demo_video.py build SPEC.json                        render the demo described by SPEC

Crops are in source pixels. With a 2x capture, double the CSS pixels.

Segment types (see example-spec.json):
  clean   the flow full frame with no text, played as recorded
  card    a text-only title card
  step    captions on the left and the zoomed clip on the right. A step stays up
          until its caption can be read. The clip loops or holds its last frame
          to fill that time and always ends on a finished action.
  banner  full frame with a title band along the bottom
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

WIDTH, HEIGHT = 1920, 1080
PANEL_X = 768  # left caption column; the zoomed clip fills the rest
READING = {"cps": 14, "lead": 1.2, "min": 3.0}  # characters per second while also watching the clip
LOOP_AT = 3.0  # clips shorter than this play once and hold; longer ones loop
SETTLE = 0.6  # stillness after the last action before the next cut


def run(cmd):
    subprocess.run(cmd, check=True)


def cfr(args):
    run(["ffmpeg", "-v", "error", "-y", "-i", args.source, "-vf", f"fps={args.fps}",
         "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-pix_fmt", "yuv420p", args.out])
    print(args.out)


def frames(args):
    os.makedirs(args.outdir, exist_ok=True)
    for t in args.at:
        out = os.path.join(args.outdir, f"f{t}.png")
        vf = []
        if args.crop:
            x, y, w, h = args.crop.split(",")
            vf = ["-vf", f"crop={w}:{h}:{x}:{y}"]
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", args.source, "-frames:v", "1", *vf, out])
        print(out)


def esc(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def wrap(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def kind(segment):
    if "type" in segment:
        return segment["type"]
    return "banner" if segment.get("crop", {}) is None else "step"


def clips(segment):
    """A step can cut between several clips under one caption."""
    if "clips" in segment:
        return [{"speed": segment.get("speed", 1), "crop": segment.get("crop"), **clip} for clip in segment["clips"]]
    return [{"start": segment["start"], "end": segment["end"], "speed": segment.get("speed", 1), "crop": segment.get("crop")}]


def read_time(segment, reading):
    chars = len(segment.get("title", "")) + len(segment.get("subtitle", ""))
    return max(reading["min"], reading["lead"] + chars / reading["cps"]), chars


def plan(spec):
    """Decide how long every segment stays up and what its clip does meanwhile."""
    reading = {**READING, **spec.get("reading", {})}
    loop_at, fade = spec.get("loop_at", LOOP_AT), spec.get("fade", 0.4)
    rows = []
    for index, segment in enumerate(spec["segments"]):
        type_ = kind(segment)
        lead_in = fade + 0.2 if index else 0.0  # hold the first frame so the action starts after the crossfade
        if type_ == "card":
            read, chars = read_time(segment, {**reading, "min": 2.0, "lead": 1.0})
            rows.append({"type": type_, "chars": chars, "read": read, "clip": 0, "plays": 0, "mode": "text", "lead_in": 0, "tail": 0, "total": segment.get("duration", read)})
            continue
        clip = sum((c["end"] - c["start"]) / c["speed"] for c in clips(segment))
        if type_ == "clean":
            rows.append({"type": type_, "chars": 0, "read": 0, "clip": clip, "plays": 1, "mode": "once", "lead_in": 0, "tail": 0, "total": clip})
            continue
        read, chars = read_time(segment, reading)
        mode = segment.get("after") or ("loop" if clip >= loop_at else "hold")
        plays = 1
        if mode == "loop":
            # Whole plays that fit, then the finished frame holds for the rest. A cut never lands mid-action.
            plays = max(1, math.floor((read - lead_in - SETTLE) / clip))
        tail = max(SETTLE, read - lead_in - plays * clip)
        if index == len(spec["segments"]) - 1:
            tail += spec.get("hold", 1.5)
        rows.append({"type": type_, "chars": chars, "read": read, "clip": clip, "plays": plays,
                     "mode": "once" if clip + lead_in + SETTLE >= read else mode,
                     "lead_in": lead_in, "tail": tail, "total": lead_in + plays * clip + tail})
    return rows


def print_plan(spec, rows):
    fade = spec.get("fade", 0.4)
    print(f"{'#':>2}  {'type':6} {'chars':>5} {'read':>5} {'clip':>5}  {'clip does':12} {'on screen':>9}  title")
    for index, (segment, row) in enumerate(zip(spec["segments"], rows)):
        does = {"loop": f"loops x{row['plays']}", "hold": "plays, holds", "once": "plays once", "text": "-"}[row["mode"]]
        print(f"{index:>2}  {row['type']:6} {row['chars']:>5} {row['read']:>5.1f} {row['clip']:>5.1f}  {does:12} {row['total']:>8.1f}s  {segment.get('title', '')}")
    total = sum(row["total"] for row in rows) - fade * (len(rows) - 1)
    print(f"total {total:.1f}s")
    return total


def render_segment(spec, segment, row, source, out, work, index):
    fps = spec.get("fps", 30)
    regular, medium = spec["fonts"]["regular"], spec["fonts"]["medium"]
    colors = {"background": "0x0e0f12", "accent": "0xf0b44c", "muted": "0x9a9ca3",
              "eyebrow": "0x6b6e76", "rule": "0x26282e", **spec.get("colors", {})}
    bg, type_ = colors["background"], row["type"]
    encode = ["-c:v", "libx264", "-preset", "fast", "-crf", "12", "-pix_fmt", "yuv420p", "-r", str(fps)]
    title, subtitle = segment.get("title", ""), segment.get("subtitle", "")

    if type_ == "card":
        text = []
        if segment.get("eyebrow", spec.get("eyebrow")):
            text.append(f"drawtext=fontfile='{regular}':text='{esc(segment.get('eyebrow', spec.get('eyebrow')))}':fontcolor={colors['eyebrow']}:fontsize=30:x=(w-tw)/2:y=h/2-90")
        text.append(f"drawtext=fontfile='{medium}':text='{esc(title)}':fontcolor=white:fontsize=84:x=(w-tw)/2:y=h/2-30")
        if subtitle:
            text.append(f"drawtext=fontfile='{regular}':text='{esc(subtitle)}':fontcolor={colors['muted']}:fontsize=34:x=(w-tw)/2:y=h/2+80")
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={bg}:s={WIDTH}x{HEIGHT}:r={fps}:d={row['total']:.3f}",
             "-vf", ",".join(text), *encode, out])
        return

    # Pass 1: the clip alone, cut, sped and framed, so a step can loop it whole.
    default_crop = spec.get("crop", {})
    parts, labels = [], []
    for n, clip in enumerate(clips(segment)):
        chain = f"[0:v]trim=start={clip['start']}:end={clip['end']},setpts=(PTS-STARTPTS)/{clip['speed']},fps={fps}"
        if type_ == "step":
            box = {**default_crop, **(clip.get("crop") or {})}
            chain += f",crop={box['w']}:{box['h']}:{box['x']}:{box['y']}"
            chain += f",scale={WIDTH - PANEL_X}:{HEIGHT}:flags=lanczos:force_original_aspect_ratio=decrease"
            chain += f",pad={WIDTH}:{HEIGHT}:{PANEL_X}+({WIDTH - PANEL_X}-iw)/2:(oh-ih)/2:color={bg}"
        else:
            chain += f",scale={WIDTH}:{HEIGHT}:flags=lanczos:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color={bg}"
        parts.append(chain + f",setsar=1,format=yuv420p[c{n}]")
        labels.append(f"[c{n}]")
    parts.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[out]")
    media = os.path.join(work, f"media{index:02}.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", source, "-filter_complex", ";".join(parts), "-map", "[out]", *encode, media])
    if type_ == "clean":
        shutil.copy(media, out)
        return

    # Pass 2: loop whole plays, hold the ends, and lay the caption over the top.
    # The pads set the length exactly. An output -t trims the lead-in instead of the end.
    chain = f"tpad=start_mode=clone:start_duration={row['lead_in']:.3f}:stop_mode=clone:stop_duration={row['tail']:.3f}"
    if type_ == "banner":
        chain += f",drawbox=x=0:y=ih-200:w=iw:h=200:color={bg}@0.92:t=fill"
        chain += f",drawtext=fontfile='{medium}':text='{esc(title)}':fontcolor=white:fontsize=56:x=96:y=h-160"
        chain += f",drawtext=fontfile='{regular}':text='{esc(subtitle)}':fontcolor={colors['muted']}:fontsize=30:x=96:y=h-86"
    else:
        chain += f",drawbox=x={PANEL_X - 1}:y=0:w=1:h={HEIGHT}:color={colors['rule']}:t=fill"
        if spec.get("eyebrow"):
            chain += f",drawtext=fontfile='{regular}':text='{esc(spec['eyebrow'])}':fontcolor={colors['eyebrow']}:fontsize=26:x=96:y=88"
        if segment.get("step"):
            chain += f",drawtext=fontfile='{medium}':text='{esc(segment['step'])}':fontcolor={colors['accent']}:fontsize=34:x=96:y=380"
        y = 432
        for line in wrap(title, 22):
            chain += f",drawtext=fontfile='{medium}':text='{esc(line)}':fontcolor=white:fontsize=60:x=96:y={y}"
            y += 72
        y += 18
        for line in wrap(subtitle, 34):
            chain += f",drawtext=fontfile='{regular}':text='{esc(line)}':fontcolor={colors['muted']}:fontsize=32:x=96:y={y}"
            y += 46
    run(["ffmpeg", "-v", "error", "-y", "-stream_loop", str(row["plays"] - 1), "-i", media,
         "-vf", chain, *encode, out])


def build(args):
    with open(args.spec) as handle:
        spec = json.load(handle)
    base = os.path.dirname(os.path.abspath(args.spec))
    path = lambda value: value if os.path.isabs(value) else os.path.join(base, value)
    source, output = path(spec["source"]), path(spec["output"])
    fps, fade = spec.get("fps", 30), spec.get("fade", 0.4)
    rows = plan(spec)
    planned = print_plan(spec, rows)
    if args.dry:
        return

    work = tempfile.mkdtemp(prefix="demo-video-")
    files = []
    for index, (segment, row) in enumerate(zip(spec["segments"], rows)):
        out = os.path.join(work, f"seg{index:02}.mp4")
        render_segment(spec, segment, row, source, out, work, index)
        actual = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                                      check=True, capture_output=True, text=True).stdout)
        if abs(actual - row["total"]) > 0.1:
            sys.exit(f"segment {index} rendered {actual:.2f}s, planned {row['total']:.2f}s; kept {work}")
        files.append(out)

    inputs, parts = [], []
    for index, file in enumerate(files):
        inputs += ["-i", file]
        parts.append(f"[{index}:v]fps={fps},format=yuv420p,settb=1/{fps}[s{index}]")
    current, offset = "s0", 0.0
    for index in range(1, len(files)):
        offset += rows[index - 1]["total"] - fade
        parts.append(f"[{current}][s{index}]xfade=transition=fade:duration={fade}:offset={offset:.3f}[x{index}]")
        current = f"x{index}"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";\n".join(parts), "-map", f"[{current}]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps),
         "-movflags", "+faststart", output])
    shutil.rmtree(work, ignore_errors=True)
    print(f"{output}  planned {planned:.1f}s")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("cfr"); p.add_argument("source"); p.add_argument("out"); p.add_argument("--fps", type=int, default=30); p.set_defaults(func=cfr)
    p = commands.add_parser("frames"); p.add_argument("source"); p.add_argument("outdir")
    p.add_argument("--at", nargs="+", type=float, required=True); p.add_argument("--crop"); p.set_defaults(func=frames)
    p = commands.add_parser("plan"); p.add_argument("spec"); p.set_defaults(func=build, dry=True)
    p = commands.add_parser("build"); p.add_argument("spec"); p.set_defaults(func=build, dry=False)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
