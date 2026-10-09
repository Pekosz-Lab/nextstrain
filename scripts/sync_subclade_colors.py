#!/usr/bin/env python3
"""
Sync config/{h3n2,h1n1,vic}/colors.tsv with the subclade colours used by the
official Nextstrain seasonal-flu builds.

Where the official colours live
-------------------------------
nextstrain/seasonal-flu hard-codes them in each lineage's HA Auspice config:
    config/<lineage>/ha/auspice_config.json -> colorings[key == "subclade"].scale
They are curated by hand; when a new subclade gets a colour, Nextstrain often
re-assigns the colours of the existing subclades too (the whole palette shifts).
So this script always replaces the *whole* coloured block, never appends to it.

What it writes
--------------
config/<subtype>/colors.tsv, plain rows only (`subclade<TAB>value<TAB>#hex`, no
header or comment lines):
    1. coloured block: the official scale, in the official order (= legend order)
    2. grey block:     every other subclade already in the local file, plus any
                       subclade the official scale dropped, plus --add-grey values,
                       re-shaded light -> dark in nomenclature order using the same
                       grey ramp Auspice uses for unlisted values. The grey block
                       starts at the first row coloured #BDC3C6.
config/subclade_colors_source.tsv, the provenance of the coloured blocks: one row
per subtype with the seasonal-flu file and commit copied, and the sync date.

Usage (from the repository root, inside the pipeline's conda environment)
-----
    python scripts/sync_subclade_colors.py            # update all three files
    python scripts/sync_subclade_colors.py --check    # report only; exit 1 if out of date
    python scripts/sync_subclade_colors.py --check --auspice-dir auspice
                                                      # also list subclades in the built
                                                      # Auspice JSONs that have no colour
Then review `git diff config/*/colors.tsv` and commit.

Standard library only.
"""
import argparse
import datetime
import glob
import json
import math
import os
import re
import sys
import urllib.request

REPO = "nextstrain/seasonal-flu"
LOCAL_TO_OFFICIAL = {"h3n2": "h3n2", "h1n1": "h1n1pdm", "vic": "vic"}
OFFICIAL_PATH = "config/{lineage}/ha/auspice_config.json"
TRAIT = "subclade"
GREY_RANGE = ("#BDC3C6", "#868992")  # Auspice's ramp for values missing from a scale


# --------------------------------------------------------------------------- fetch
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pekosz-lab-nextstrain-color-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def official_scale(lineage, ref):
    """Return (scale, source) for one lineage; source = (file, commit, commit date)."""
    path = OFFICIAL_PATH.format(lineage=lineage)
    config = json.loads(fetch(f"https://raw.githubusercontent.com/{REPO}/{ref}/{path}"))
    scale = next((c.get("scale") for c in config["colorings"] if c["key"] == TRAIT), None)
    if not scale:
        sys.exit(f"ERROR: no '{TRAIT}' scale in {REPO}/{path}@{ref}. Has the official config changed shape?")
    for value, hexcode in scale:
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", hexcode):
            sys.exit(f"ERROR: official colour for {value} is not a 6-digit hex code: {hexcode}")
    try:  # record which commit the colours came from (best effort)
        api = f"https://api.github.com/repos/{REPO}/commits?path={path}&sha={ref}&per_page=1"
        c = json.loads(fetch(api))[0]
        source = (f"{REPO}/{path}", c["sha"][:7], c["commit"]["committer"]["date"][:10])
    except Exception:
        source = (f"{REPO}/{path}", ref, "unknown")
    return [(v, h.upper()) for v, h in scale], source


# --------------------------------------------------------------- local colors.tsv
def read_local(path):
    """Return (rows, n_coloured). The coloured block ends at the first row with the
    grey-ramp start colour (#BDC3C6); comment or blank lines are skipped if present."""
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or not line.strip():
                    continue
                f = line.rstrip("\r\n").split("\t")
                if len(f) == 3 and f[0].lower() == TRAIT:
                    rows.append((f[1], f[2].upper()))
    n_coloured = next((i for i, (_, h) in enumerate(rows) if h == GREY_RANGE[0]), len(rows))
    return rows, n_coloured


def natural_key(v):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", v)]


# ------------------------------------------- grey ramp identical to Auspice / d3
# d3-color Lab/HCL constants and d3-interpolate interpolateHcl.
Xn, Yn, Zn = 0.96422, 1.0, 0.82521
t0, t1 = 4 / 29, 6 / 29
t2, t3 = 3 * t1 * t1, t1 ** 3


def _rgb2lrgb(x):
    x /= 255
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def _lrgb2rgb(x):
    return 255 * (12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055)


def _xyz2lab(t):
    return t ** (1 / 3) if t > t3 else t / t2 + t0


def _lab2xyz(t):
    return t ** 3 if t > t1 else t2 * (t - t0)


def _hex2hcl(h):
    r, g, b = (_rgb2lrgb(int(h[i:i + 2], 16)) for i in (1, 3, 5))
    y = _xyz2lab((0.2225045 * r + 0.7168786 * g + 0.0606169 * b) / Yn)
    if r == g == b:
        x = z = y
    else:
        x = _xyz2lab((0.4360747 * r + 0.3850649 * g + 0.1430804 * b) / Xn)
        z = _xyz2lab((0.0139322 * r + 0.0971045 * g + 0.7141733 * b) / Zn)
    L, A, B = 116 * y - 16, 500 * (x - y), 200 * (y - z)
    hue = math.degrees(math.atan2(B, A)) % 360
    return hue, math.hypot(A, B), L


def _hcl2hex(hue, c, L):
    a, b = math.cos(math.radians(hue)) * c, math.sin(math.radians(hue)) * c
    y = (L + 16) / 116
    x, z = y + a / 500, y - b / 200
    x, y, z = Xn * _lab2xyz(x), Yn * _lab2xyz(y), Zn * _lab2xyz(z)
    rgb = (_lrgb2rgb(3.1338561 * x - 1.6168667 * y - 0.4906146 * z),
           _lrgb2rgb(-0.9787684 * x + 1.9161415 * y + 0.0334540 * z),
           _lrgb2rgb(0.0719453 * x - 0.2289914 * y + 1.4052427 * z))
    # d3 rounds to the nearest integer and clamps to 0-255
    return "#" + "".join(f"{max(0, min(255, int(math.floor(v + 0.5)))):02X}" for v in rgb)


def grey_ramp(n):
    """Auspice createListOfColors(n, GREY_RANGE): n colours at 0..n-1 of a [0, n] HCL scale."""
    (h0, c0, l0), (h1, c1, l1) = (_hex2hcl(x) for x in GREY_RANGE)
    dh = h1 - h0
    if dh > 180 or dh < -180:
        dh -= 360 * round(dh / 360)
    return [_hcl2hex(h0 + dh * t, c0 + (c1 - c0) * t, l0 + (l1 - l0) * t)
            for t in (i / n for i in range(n))]


# --------------------------------------------------------------------- main
def build_rows(scale, local_rows, add_grey):
    coloured = [v for v, _ in scale]
    seen = {v.lower() for v in coloured}
    greys = []
    for v in [v for v, _ in local_rows] + list(add_grey):
        if v.lower() not in seen:
            greys.append(v)
            seen.add(v.lower())
    greys.sort(key=natural_key)
    return list(scale) + list(zip(greys, grey_ramp(len(greys))))


def render(rows):
    """colors.tsv content: data rows only, no header or comments."""
    return "".join(f"{TRAIT}\t{v}\t{h}\n" for v, h in rows)


def write_provenance(path, provenance):
    """Update config/subclade_colors_source.tsv, keeping rows of subtypes not synced now."""
    header = ["subtype", "official_file", "official_commit", "official_commit_date", "synced_on"]
    rows = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh.read().splitlines()[1:]:
                f = line.split("\t")
                if len(f) == len(header):
                    rows[f[0]] = f
    rows.update(provenance)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(header) + "\n")
        for st in sorted(rows):
            fh.write("\t".join(rows[st]) + "\n")


def built_subclades(auspice_dir, subtype):
    vals = set()
    for f in glob.glob(os.path.join(auspice_dir, subtype, "*.json")):
        if f.endswith("_tip-frequencies.json"):
            continue
        stack = [json.load(open(f, encoding="utf-8"))["tree"]]
        while stack:
            n = stack.pop()
            v = n.get("node_attrs", {}).get(TRAIT, {}).get("value")
            if v not in (None, "", "unknown", "?"):
                vals.add(str(v))
            stack.extend(n.get("children", []))
    return vals


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", default="config", help="directory holding <subtype>/colors.tsv")
    p.add_argument("--ref", default="master", help="seasonal-flu branch, tag or commit to copy from")
    p.add_argument("--subtypes", nargs="+", default=list(LOCAL_TO_OFFICIAL), choices=list(LOCAL_TO_OFFICIAL))
    p.add_argument("--add-grey", nargs="*", default=[], metavar="SUBCLADE",
                   help="extra subclades to list in grey (applied to every subtype given)")
    p.add_argument("--check", action="store_true", help="report differences only; exit 1 if any file is out of date")
    p.add_argument("--auspice-dir", help="with --check: also list subclades in built JSONs that have no colour")
    args = p.parse_args()

    prov_path = os.path.join(args.config_dir, "subclade_colors_source.tsv")
    recorded = set()
    if os.path.exists(prov_path):
        with open(prov_path, encoding="utf-8") as fh:
            recorded = {line.split("\t")[0] for line in fh.read().splitlines()[1:]}
    provenance = {}
    out_of_date = False
    for st in args.subtypes:
        path = os.path.join(args.config_dir, st, "colors.tsv")
        scale, source = official_scale(LOCAL_TO_OFFICIAL[st], args.ref)
        local, n_old_coloured = read_local(path)
        rows = build_rows(scale, local, args.add_grey)
        old, new = dict(local), dict(rows)
        old_col = [v for v, _ in local][:n_old_coloured]

        changes = []
        for v, h in scale:
            if v not in old:
                changes.append(f"  + {v} {h}  (new subclade colour)")
            elif old[v] != h:
                changes.append(f"  ~ {v} {old[v]} -> {h}")
        coloured_now = {v for v, _ in scale}
        for v in new:
            if v not in old and v not in coloured_now:
                changes.append(f"  + {v} {new[v]}  (grey)")
        for v in old:
            if v not in new:
                changes.append(f"  - {v} (removed)")
        for v in set(old_col) - {s for s, _ in scale}:
            changes.append(f"  > {v} now grey (no longer coloured in the official build)")
        if [v for v, _ in local] != [v for v, _ in rows] and not changes:
            changes.append("  order / grey shades updated")
        if not changes and render(rows) != (open(path, encoding="utf-8").read() if os.path.exists(path) else ""):
            changes.append("  formatting only (comment lines, line endings)")

        print(f"[{st}] official: {source[0]} @ {source[1]} ({source[2]})")
        print("\n".join(changes) if changes else "  up to date")

        if args.check and args.auspice_dir:
            missing = sorted(built_subclades(args.auspice_dir, st) - {v for v, _ in rows}, key=natural_key)
            if missing:
                out_of_date = True
                print(f"  ! in {args.auspice_dir}/{st} but not in colors.tsv (Auspice shows these grey, "
                      f"appended to the legend): {', '.join(missing)}")
                print("    The official build has no colour for these either, so they are grey there too.\n"
                      "    Either wait for Nextstrain to assign one and re-sync, or list them with a fixed grey:\n"
                      f"    python scripts/sync_subclade_colors.py --subtypes {st} --add-grey {' '.join(missing)}")

        if changes:
            out_of_date = out_of_date or bool([c for c in changes if not c.startswith("  formatting")])
            if not args.check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(render(rows))
                print(f"  wrote {path}")
        if not args.check and (changes or st not in recorded):
            provenance[st] = [st, *source, datetime.date.today().isoformat()]

    if provenance:
        write_provenance(prov_path, provenance)
        print(f"recorded the source of {', '.join(sorted(provenance))} in {prov_path}")

    if args.check and out_of_date:
        print("\nColours need attention (see above). After updating, review `git diff config/*/colors.tsv`.")
        sys.exit(1)


if __name__ == "__main__":
    main()
