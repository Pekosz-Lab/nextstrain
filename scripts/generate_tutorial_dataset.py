#!/usr/bin/env python3
"""Create a small, reproducible influenza tutorial dataset from fludb.

The output contains 20 distinct samples for each of H1N1, H3N2, and
B/Victoria. Samples are divided among segment profiles that exercise the
diagnostic workflow:

    12 complete genomes
     2 HA-only samples
     2 NA-only samples
     3 samples with every segment except HA and NA
     1 NS-only sample

All source records are complete genomes. The partial profiles are produced by
asking ``fludb/scripts/download.py`` to export only the desired segments.
"""

from __future__ import annotations

import argparse
import csv
import random
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
from collections import defaultdict
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
ALL_SEGMENTS = ("pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns")
SUBTYPES = ("H1N1", "H3N2", "Victoria")

# These counts sum to 20 samples per subtype.
PROFILE_SEGMENTS = {
    "complete": ALL_SEGMENTS,
    "ha_only": ("ha",),
    "na_only": ("na",),
    "without_ha_na": ("pb2", "pb1", "pa", "np", "mp", "ns"),
    "ns_only": ("ns",),
}
PROFILE_COUNTS = {
    "complete": 12,
    "ha_only": 2,
    "na_only": 2,
    "without_ha_na": 3,
    "ns_only": 1,
}

METADATA_COLUMNS = (
    "sequence_ID",
    "sample_ID",
    "sequencing_run",
    "date",
    "passage_history",
)

# JHH uses GenBank segment numbering. Influenza B swaps PB1 and PB2 relative
# to the Influenza A numbering used by the rest of the segments.
IAV_SEGMENT_NUMBERS = {
    "pb2": "1",
    "pb1": "2",
    "pa": "3",
    "ha": "4",
    "np": "5",
    "na": "6",
    "mp": "7",
    "ns": "8",
}
IBV_SEGMENT_NUMBERS = {
    **IAV_SEGMENT_NUMBERS,
    "pb1": "1",
    "pb2": "2",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=REPOSITORY / "fludb.db",
        help="SQLite influenza database (default: repository fludb.db).",
    )
    parser.add_argument(
        "--download-script",
        type=Path,
        default=REPOSITORY / "fludb" / "scripts" / "download.py",
        help="Path to fludb download.py.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY / "tutorial",
        help="Directory for JHH_sequences.fasta and JHH_metadata.txt.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260807,
        help="Random seed used for reproducible downsampling.",
    )
    return parser.parse_args()


def select_samples(db_path: Path, seed: int) -> dict[str, dict[str, list[str]]]:
    """Select 20 distinct complete genomes per subtype, reproducibly."""
    required = sum(PROFILE_COUNTS.values())
    complete_clause = " AND ".join(
        f"{segment} IS NOT NULL AND {segment} != ''" for segment in ALL_SEGMENTS
    )
    selected: dict[str, dict[str, list[str]]] = {}

    with sqlite3.connect(db_path) as connection:
        for subtype_index, subtype in enumerate(SUBTYPES):
            rows = connection.execute(
                f"""
                SELECT sequence_ID
                FROM influenza_genomes
                WHERE subtype = ? AND {complete_clause}
                ORDER BY sequence_ID
                """,
                (subtype,),
            ).fetchall()
            candidates = [row[0] for row in rows]
            if len(candidates) < required:
                raise RuntimeError(
                    f"{subtype} has only {len(candidates)} complete genomes; "
                    f"{required} are required."
                )

            # Give each subtype an independent, stable shuffle.
            rng = random.Random(seed + subtype_index)
            rng.shuffle(candidates)
            chosen = candidates[:required]

            selected[subtype] = {}
            offset = 0
            for profile, count in PROFILE_COUNTS.items():
                selected[subtype][profile] = chosen[offset : offset + count]
                offset += count

    return selected


def sql_string(value: str) -> str:
    """Quote a trusted database value for download.py's SQL filter option."""
    return "'" + value.replace("'", "''") + "'"


def run_download(
    download_script: Path,
    db_path: Path,
    subtype: str,
    profile: str,
    sequence_ids: list[str],
    temp_dir: Path,
) -> tuple[Path, Path]:
    """Call download.py once for one subtype/profile group."""
    stem = f"{subtype.lower()}_{profile}"
    fasta_path = temp_dir / f"{stem}.fasta"
    metadata_path = temp_dir / f"{stem}.tsv"
    id_list = ", ".join(sql_string(sequence_id) for sequence_id in sequence_ids)

    command = [
        sys.executable,
        str(download_script),
        "--db",
        str(db_path),
        "--fasta",
        str(fasta_path),
        "--metadata",
        str(metadata_path),
        "--headers",
        "sequence_ID",
        "segment",
        "--header-delimiter",
        "_",
        "--filters",
        f"sequence_ID IN ({id_list})",
        "--segments",
        *PROFILE_SEGMENTS[profile],
    ]
    subprocess.run(command, check=True, cwd=REPOSITORY)
    return fasta_path, metadata_path


def read_downloaded_fasta(path: Path) -> list[tuple[str, str, str]]:
    """Read download.py output as (sequence_ID, segment, sequence) tuples."""
    records: list[tuple[str, str, str]] = []
    header: str | None = None
    sequence_lines: list[str] = []

    def save_record() -> None:
        if header is None:
            return
        try:
            sequence_id, segment = header.rsplit("_", 1)
        except ValueError as error:
            raise RuntimeError(f"Unexpected FASTA header in {path}: {header}") from error
        # download.py currently inserts an empty field before the segment when
        # 'segment' is requested as a header, yielding sequence_ID__segment.
        sequence_id = sequence_id.rstrip("_")
        if segment not in ALL_SEGMENTS:
            raise RuntimeError(f"Unknown segment in {path}: {segment}")
        sequence = "".join(sequence_lines)
        if not sequence:
            raise RuntimeError(f"Empty sequence in {path}: {header}")
        records.append((sequence_id, segment, sequence))

    with path.open() as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line.startswith(">"):
                save_record()
                header = line[1:]
                sequence_lines = []
            elif line:
                sequence_lines.append(line)
    save_record()
    return records


def write_outputs(
    selected: dict[str, dict[str, list[str]]],
    downloads: list[tuple[str, str, Path, Path]],
    fasta_output: Path,
    metadata_output: Path,
) -> int:
    """Normalize, validate, and combine temporary download.py outputs."""
    expected: dict[str, set[str]] = {}
    subtype_by_id: dict[str, str] = {}
    for subtype, profiles in selected.items():
        for profile, sequence_ids in profiles.items():
            for sequence_id in sequence_ids:
                expected[sequence_id] = set(PROFILE_SEGMENTS[profile])
                subtype_by_id[sequence_id] = subtype

    observed: dict[str, set[str]] = defaultdict(set)
    fasta_records: list[tuple[str, str]] = []
    metadata_by_id: dict[str, dict[str, str]] = {}
    fasta_headers: set[str] = set()

    for subtype, _profile, fasta_path, metadata_path in downloads:
        segment_numbers = IBV_SEGMENT_NUMBERS if subtype == "Victoria" else IAV_SEGMENT_NUMBERS
        for sequence_id, segment, sequence in read_downloaded_fasta(fasta_path):
            output_header = f"{sequence_id}_{segment_numbers[segment]}"
            if output_header in fasta_headers:
                raise RuntimeError(f"Duplicate output FASTA header: {output_header}")
            fasta_headers.add(output_header)
            observed[sequence_id].add(segment)
            fasta_records.append((output_header, sequence))

        with metadata_path.open(newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                metadata_by_id[row["sequence_ID"]] = row

    if observed != expected:
        differences = {
            sequence_id: {
                "expected": sorted(expected.get(sequence_id, set())),
                "observed": sorted(observed.get(sequence_id, set())),
            }
            for sequence_id in expected.keys() | observed.keys()
            if expected.get(sequence_id, set()) != observed.get(sequence_id, set())
        }
        raise RuntimeError(f"Downloaded segment profiles did not match selection: {differences}")

    ordered_ids = [
        sequence_id
        for subtype in SUBTYPES
        for profile in PROFILE_SEGMENTS
        for sequence_id in selected[subtype][profile]
    ]
    if set(metadata_by_id) != set(ordered_ids):
        raise RuntimeError("Downloaded metadata IDs do not match the selected sample IDs.")

    with fasta_output.open("w") as handle:
        for output_header, sequence in fasta_records:
            handle.write(f">{output_header}\n")
            handle.write("\n".join(textwrap.wrap(sequence, width=80)) + "\n")

    with metadata_output.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=METADATA_COLUMNS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for sequence_id in ordered_ids:
            writer.writerow({column: metadata_by_id[sequence_id].get(column, "") for column in METADATA_COLUMNS})

    # Confirm that selection really is 20 unique samples for every subtype.
    for subtype in SUBTYPES:
        subtype_ids = {sequence_id for profile in selected[subtype].values() for sequence_id in profile}
        if len(subtype_ids) != 20:
            raise RuntimeError(f"Expected 20 unique {subtype} samples, found {len(subtype_ids)}.")
        if any(subtype_by_id[sequence_id] != subtype for sequence_id in subtype_ids):
            raise RuntimeError(f"Subtype bookkeeping failed for {subtype}.")

    return len(fasta_records)


def main() -> None:
    args = parse_args()
    db_path = args.db.resolve()
    download_script = args.download_script.resolve()
    output_dir = args.output_dir.resolve()

    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")
    if not download_script.is_file():
        raise FileNotFoundError(f"download.py not found: {download_script}")

    output_dir.mkdir(parents=True, exist_ok=True)
    fasta_output = output_dir / "JHH_sequences.fasta"
    metadata_output = output_dir / "JHH_metadata.txt"
    selected = select_samples(db_path, args.seed)

    # Build and validate in a temporary directory so a failed run cannot leave
    # partially written tutorial outputs behind.
    with tempfile.TemporaryDirectory(prefix="jhh_tutorial_", dir=output_dir) as temp_name:
        temp_dir = Path(temp_name)
        downloads: list[tuple[str, str, Path, Path]] = []
        for subtype in SUBTYPES:
            for profile in PROFILE_SEGMENTS:
                fasta_path, metadata_path = run_download(
                    download_script,
                    db_path,
                    subtype,
                    profile,
                    selected[subtype][profile],
                    temp_dir,
                )
                downloads.append((subtype, profile, fasta_path, metadata_path))

        temp_fasta = temp_dir / fasta_output.name
        temp_metadata = temp_dir / metadata_output.name
        fasta_record_count = write_outputs(
            selected,
            downloads,
            temp_fasta,
            temp_metadata,
        )
        temp_fasta.replace(fasta_output)
        temp_metadata.replace(metadata_output)

    print(f"Wrote {fasta_output}")
    print(f"Wrote {metadata_output}")
    print(f"60 samples (20 per subtype), {fasta_record_count} segment records")
    for profile, count in PROFILE_COUNTS.items():
        print(f"  {profile}: {count} samples per subtype")


if __name__ == "__main__":
    main()
