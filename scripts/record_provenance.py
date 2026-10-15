#!/usr/bin/env python3
"""Print provenance lines for the run provenance file.

Called by the run handlers in workflow/snakemake_rules/reports.smk, which
append the output to .run/run_logs/{RUN_ID}_provenance.txt:

  onstart              --inputs <JHH sequences> <JHH metadata> <vaccine FASTA>
  onsuccess / onerror  --nextclade-dir nextclade/flu

Also called by rule fetch_hana_datasets (segments.smk), so the tags of the
freshly downloaded datasets appear in its log.

--inputs FILE ...    one line per file: path, FASTA record count (FASTA files
                     only), size, last modified time (UTC) and SHA-256
                     checksum. Only these summaries are printed, never any
                     sequence or metadata content. A missing file is reported
                     as MISSING (the run itself fails later, in ingest).
--nextclade-dir DIR  one line per Nextclade dataset under DIR (any folder with
                     a pathogen.json): folder, dataset name, version tag.

Output: stdout only. Exits 0 even when a file is missing, because provenance
must never stop a run; it exits non-zero only on bad arguments.
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path

FASTA_SUFFIXES = {".fasta", ".fa", ".fna", ".fas"}


def describe_file(path):
    """One summary line for an input file."""
    if not path.is_file():
        return f"{path}  MISSING"
    sha256 = hashlib.sha256()
    records = 0
    with path.open("rb") as handle:
        for line in handle:
            sha256.update(line)
            if line.startswith(b">"):
                records += 1
    stat = path.stat()
    modified = datetime.datetime.fromtimestamp(stat.st_mtime, datetime.timezone.utc)
    fields = [str(path)]
    if path.suffix.lower() in FASTA_SUFFIXES:
        fields.append(f"records={records}")
    fields += [
        f"bytes={stat.st_size}",
        f"modified_utc={modified:%Y-%m-%dT%H:%M:%SZ}",
        f"sha256={sha256.hexdigest()}",
    ]
    return "  ".join(fields)


def describe_datasets(root):
    """One line per Nextclade dataset (folder holding a pathogen.json)."""
    lines = []
    for pathogen in sorted(root.glob("**/pathogen.json")):
        folder = pathogen.parent.relative_to(root)
        try:
            meta = json.loads(pathogen.read_text())
            name = meta.get("attributes", {}).get("name", "unknown")
            tag = meta.get("version", {}).get("tag", "untagged")
        except (OSError, ValueError, AttributeError) as error:
            name, tag = "unreadable", f"error: {error}"
        lines.append(f"{folder}  tag={tag}  name={name}")
    return lines or [f"no Nextclade datasets found under {root}"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inputs", nargs="+", type=Path, metavar="FILE",
                        help="input files to summarise")
    parser.add_argument("--nextclade-dir", type=Path, metavar="DIR",
                        help="folder holding the Nextclade datasets")
    args = parser.parse_args()
    if not args.inputs and not args.nextclade_dir:
        parser.error("give --inputs and/or --nextclade-dir")

    if args.inputs:
        print("== input files ==")
        for path in args.inputs:
            print(describe_file(path))
    if args.nextclade_dir:
        print("== nextclade datasets ==")
        for line in describe_datasets(args.nextclade_dir):
            print(line)


if __name__ == "__main__":
    main()
