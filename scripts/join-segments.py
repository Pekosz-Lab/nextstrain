"""
author: jameshadfield
description: This script concatenates flu genome segment FASTAs in the specified input order and provides a single file.
    Note that FASTA headers that contain "|" will be stripped from that point forward.
source: https://github.com/nextstrain/avian-flu/blob/master/scripts/join-segments.py
    - With no modifications 
"""

from Bio import SeqIO
from collections import defaultdict
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--segments', type = str, required = True, nargs='+', help = "per-segment alignments")
    parser.add_argument('--output', type = str, required = True, help = "output whole genome alignment")
    args = parser.parse_args()

    records = {}
    strain_counts = defaultdict(int)
    for fname in args.segments:
        records[fname] = {record.name:str(record.seq) for record in SeqIO.parse(fname, 'fasta')}
        for key in records[fname]: strain_counts[key]+=1
        print(f"{fname}: parsed {len(records[fname].keys())} sequences")

    with open(args.output, 'w') as fh:
        print("writing genome to ", args.output)
        for name,count in strain_counts.items():
            if count!=len(args.segments):
                print(f"Excluding {name} as it only appears in {count} segments")
                continue
            genome = "".join([records[seg][name] for seg in args.segments])
            print(f">{name}\n{genome}", file=fh)