#!/usr/bin/env python3
"""Upload the finished Auspice builds to the Pekosz Lab Nextstrain groups.

This script replaces separate legacy scripts used to upload to the private vs public repository. 

Run by a person, by hand only, after reviewing every build (wiki: Step 5,
Reviewing & Publishing Builds). Never called by Snakemake or an AI agent.

Destinations (existing URLs, do not change without updating the wiki):
    private (default)  nextstrain.org/groups/PekoszLab/seasonal/{subtype}/{build}
    public (--public)  nextstrain.org/groups/PekoszLab-Public/seasonal-flu/{subtype}/{build}

Inputs:  auspice/{subtype}/{build}.json and auspice/{subtype}/{build}_tip-frequencies.json
         for the 8 segment builds and the genome build of each subtype.
Output:  none locally; uploads with `nextstrain remote upload`.

Before uploading, the script
  - checks that every file exists (stops if any is missing),
  - for --public, checks that every build's description carries the GISAID
    acknowledgement (config/description.md, built in by `augur export`; the
    check looks for the phrase "via the GISAID Initiative") and stops if not,
  - runs `nextstrain login` (you may be asked for your own credentials),
  - shows what will go where and asks you to confirm by typing.

Examples:
    python scripts/nextstrain_upload.py --dry-run          # show the plan, upload nothing
    python scripts/nextstrain_upload.py                    # private group, all subtypes
    python scripts/nextstrain_upload.py --subtypes h3n2    # private group, H3N2 only
    python scripts/nextstrain_upload.py --public           # public group (PI approval first)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SUBTYPES = ["h1n1", "h3n2", "vic"] # you can remove as you wish.
# Phrase from the GISAID acknowledgement in config/description.md.
GISAID_ACKNOWLEDGEMENT = "via the GISAID Initiative" # for the public-facing builds only
BUILDS = ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns", "genome"]
GROUPS = {
    False: ("PekoszLab", "nextstrain.org/groups/PekoszLab/seasonal", "PRIVATE (group members only)"),
    True: ("PekoszLab-Public", "nextstrain.org/groups/PekoszLab-Public/seasonal-flu", "PUBLIC (anyone on the internet)"),
}


def build_files(auspice_dir, subtype):
    """The main JSON and tip-frequencies sidecar of every build of a subtype."""
    files = []
    for build in BUILDS:
        files.append(auspice_dir / subtype / f"{build}.json")
        files.append(auspice_dir / subtype / f"{build}_tip-frequencies.json")
    return files


def lacks_gisaid_acknowledgement(main_json):
    """True if the build's description (meta.description) lacks the GISAID acknowledgement."""
    try:
        description = json.loads(main_json.read_text()).get("meta", {}).get("description", "")
    except (OSError, ValueError) as error:
        sys.exit(f"ERROR: cannot read {main_json}: {error}")
    return GISAID_ACKNOWLEDGEMENT not in " ".join(description.split())


def main():
    parser = argparse.ArgumentParser(
        description="Upload reviewed Auspice builds to the Pekosz Lab Nextstrain groups.")
    parser.add_argument("--public", action="store_true",
                        help="upload to the PUBLIC group PekoszLab-Public (needs PI approval)")
    parser.add_argument("--subtypes", nargs="+", choices=SUBTYPES, default=SUBTYPES,
                        help="subtypes to upload (default: all)")
    parser.add_argument("--auspice-dir", type=Path, default=Path("auspice"),
                        help="folder holding the builds (default: auspice)")
    parser.add_argument("--dry-run", action="store_true",
                        help="check the files and print the upload commands; upload nothing")
    args = parser.parse_args()

    group, prefix, visibility = GROUPS[args.public]
    plan = {subtype: build_files(args.auspice_dir, subtype) for subtype in args.subtypes}

    # 1. Every file must exist; a half-uploaded subtype is worse than none.
    missing = [str(f) for files in plan.values() for f in files if not f.is_file()]
    if missing:
        print(f"ERROR: {len(missing)} build file(s) missing; nothing was uploaded:")
        for f in missing:
            print(f"  {f}")
        sys.exit("Run the pipeline (wiki: Step 2) or choose subtypes with --subtypes.")

    # 2. Public builds must acknowledge GISAID (the vaccine strains come from GISAID).
    if args.public:
        unacknowledged = [str(f) for files in plan.values() for f in files[::2]
                          if lacks_gisaid_acknowledgement(f)]
        if unacknowledged:
            print(f"ERROR: these builds lack the GISAID acknowledgement ('{GISAID_ACKNOWLEDGEMENT}') in their description:")
            for f in unacknowledged:
                print(f"  {f}")
            sys.exit("Fix config/description.md, rerun the pipeline, then try again. Nothing was uploaded.")

    commands = {subtype: ["nextstrain", "remote", "upload", f"{prefix}/{subtype}"] + [str(f) for f in files]
                for subtype, files in plan.items()}

    print(f"Destination group: {group}  ->  {visibility}")
    for subtype in args.subtypes:
        print(f"  {prefix}/{subtype}/  <-  {len(BUILDS)} builds from {args.auspice_dir / subtype}/ "
              f"({', '.join(BUILDS)})")

    if args.dry_run:
        print("\nDry run: these commands would be run (nothing uploaded):")
        for command in commands.values():
            print("  " + " ".join(command))
        return

    # 3. Log in (renews your session, or asks for your own credentials).
    print("\nLogging in to Nextstrain...")
    if subprocess.run(["nextstrain", "login"]).returncode != 0:
        sys.exit("ERROR: nextstrain login failed; nothing was uploaded.")

    # 4. A person confirms by typing; the public group needs its full name.
    expected = group if args.public else "yes"
    answer = input(f"\nHave you reviewed these builds (wiki: Step 5)? "
                   f"Type '{expected}' to upload to {group}: ").strip()
    if answer != expected:
        sys.exit("Not confirmed; nothing was uploaded.")

    # 5. Upload one subtype at a time and report every result.
    failed = []
    for subtype, command in commands.items():
        print(f"\nUploading {subtype} to {prefix}/{subtype} ...")
        if subprocess.run(command).returncode == 0:
            print(f"Uploaded {subtype}.")
        else:
            print(f"ERROR: upload of {subtype} failed (see the message above).")
            failed.append(subtype)

    print(f"\nDone: {len(commands) - len(failed)} of {len(commands)} subtypes uploaded to {group}.")
    print("Record the upload: date, run ID, git commit, destination, your name (wiki: Step 5).")
    if failed:
        sys.exit(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()