#!/usr/bin/env python3

'''
2025-11-18 Elgin 

This ingests a multi-fasta file with JHH def-lines and outputs a unique sequence ID list in tsv format 

'''

import argparse
from Bio import SeqIO
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract unique strain names and segment numbers from FASTA headers like JH251234_1 (ignores segment identifier)"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input multi-FASTA file"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output TSV file"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    unique_entries = set()

    for record in SeqIO.parse(args.input, "fasta"):
        header = record.id
        try:
            strain, segment = header.split("_")
        except ValueError:
            raise ValueError(
                f"Header '{header}' does not match expected format STRAIN_SEGMENT"
            )

        unique_entries.add((strain, segment))

    df = pd.DataFrame(
        sorted(unique_entries),
        columns=["strain", "segment"]
    )

    df.to_csv(args.output, sep="\t", index=False)
    print(f"✓ Wrote {len(df)} unique entries to {args.output}")


if __name__ == "__main__":
    main()
