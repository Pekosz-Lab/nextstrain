


#!/usr/bin/env python3

'''
2025-11-18 Elgin 

This script ingests a multi-fasta file with JHH def-lines and outputs a unique sequence ID list in tsv format 

'''


import argparse
import re
import sys
from Bio import SeqIO
import csv

def parse_args():
    p = argparse.ArgumentParser(
        description="Extract unique strain IDs from FASTA headers by stripping trailing _<segment#> and deduplicating."
    )
    p.add_argument("-i", "--input", required=True, help="Input multi-FASTA file")
    p.add_argument("-o", "--output", required=True, help="Output TSV file (single column: sequence_ID)")
    return p.parse_args()

def strip_segment_suffix(seq_id: str) -> str:
    """
    Strip a trailing underscore followed by digits from the sequence id.
    Examples:
      JH25583_1  -> JH25583
      JH92010_10 -> JH92010
      ABC        -> ABC (unchanged if no trailing _digits)
    """
    return re.sub(r'_[0-9]+$', '', seq_id)

def main():
    args = parse_args()

    try:
        records = SeqIO.parse(args.input, "fasta")
    except Exception as e:
        print(f"Error opening/parsing input FASTA: {e}", file=sys.stderr)
        sys.exit(1)

    initial_count = 0
    unique_ids = set()

    for rec in records:
        initial_count += 1
        # SeqIO.record.id gives the first token of the defline (up to first whitespace)
        raw_id = rec.id
        cleaned = strip_segment_suffix(raw_id)
        unique_ids.add(cleaned)

    unique_list = sorted(unique_ids)

    # Write TSV with single column 'sequence_ID'
    try:
        with open(args.output, "w", newline="") as fh:
            writer = csv.writer(fh, delimiter="\t")
            writer.writerow(["sequence_ID"])
            for sid in unique_list:
                writer.writerow([sid])
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    print(f"Input def lines parsed: {initial_count}")
    print(f"Final unique strains: {len(unique_list)}")
    print(f"Wrote {len(unique_list)} unique sequence_IDs to {args.output}")

if __name__ == "__main__":
    main()
