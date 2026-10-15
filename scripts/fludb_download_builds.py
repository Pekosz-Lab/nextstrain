"""
Write the Nextstrain build inputs for one subtype from fludb.

Replaces fludb_download_seasonal_build.py (segments) and
fludb_download_seasonal_build_genomes.py (whole genomes).

Which fludb rows belong to a build is set in config/subtype_assignment.yaml:
the build takes every row whose `subtype` is one of its `assigned` or
`assumed` values (e.g. h1n1 = H1N1, H1xx, xxN1). Rows with any other value
(e.g. xxxx) go into no build. The `subtype` column itself is not changed, so
the build metadata still shows flusort's call (H1xx, xxN1, ...).

    # the 8 segment builds: data/{subtype}/{segment}/sequences.fasta + metadata.tsv
    python scripts/fludb_download_builds.py --subtype h1n1 --segments

    # the whole-genome build: data/{subtype}/genome/sequences.fasta + metadata.tsv
    python scripts/fludb_download_builds.py --subtype h1n1 --genome

Called by rules download_segments and download_genomes (ingest.smk).
"""

import argparse
import os
import subprocess
import sys

import yaml

SEGMENTS = ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]


def subtype_filter(config_path, build):
    """SQL condition selecting the fludb rows of one build, e.g.
    subtype IN ('H1N1', 'H1xx', 'xxN1')."""
    with open(config_path) as f:
        builds = yaml.safe_load(f)["builds"]
    if build not in builds:
        sys.exit(f"Build '{build}' is not listed in {config_path} (listed: {', '.join(builds)})")
    values = builds[build]["assigned"] + (builds[build].get("assumed") or [])
    return "subtype IN ({})".format(", ".join(f"'{v}'" for v in values))


def run(cmd):
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def download_segments(db, outdir, build, where):
    for segment in SEGMENTS:
        out = f"{outdir}/{build}/{segment}"
        os.makedirs(out, exist_ok=True)
        print(f"Downloading {build} - {segment} segment...", flush=True)
        run([
            sys.executable, "fludb/scripts/download.py",
            "--db", db,
            "--fasta", f"{out}/sequences.fasta",
            "--metadata", f"{out}/metadata.tsv",
            "--headers", "sample_ID",
            "--header-delimiter", "_",
            "--filters", where,
            "--segments", segment,
        ])


def download_genome(db, outdir, build, where):
    out = f"{outdir}/{build}/genome"
    os.makedirs(out, exist_ok=True)
    print(f"Downloading {build} - complete genomes...", flush=True)
    run([
        sys.executable, "fludb/scripts/download_concatenated.py",
        "-d", db,
        "-f", f"{out}/sequences.fasta",
        "-m", f"{out}/metadata.tsv",
        "--headers", "sequence_ID",
        "--filters", where,
        "--complete-genomes",
        "--concatenate",
    ])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--subtype", required=True, help="build to write (h1n1, h3n2 or vic)")
    what = p.add_mutually_exclusive_group(required=True)
    what.add_argument("--segments", action="store_true", help="write the 8 segment builds")
    what.add_argument("--genome", action="store_true", help="write the whole-genome build")
    p.add_argument("--db", default="fludb.db", help="fludb SQLite database (default: fludb.db)")
    p.add_argument("--outdir", default="data", help="output root (default: data)")
    p.add_argument("--config", default="config/subtype_assignment.yaml",
                   help="subtype-to-build map (default: config/subtype_assignment.yaml)")
    args = p.parse_args()

    where = subtype_filter(args.config, args.subtype)
    print(f"{args.subtype}: {where}", flush=True)
    if args.segments:
        download_segments(args.db, args.outdir, args.subtype, where)
    else:
        download_genome(args.db, args.outdir, args.subtype, where)


if __name__ == "__main__":
    main()
