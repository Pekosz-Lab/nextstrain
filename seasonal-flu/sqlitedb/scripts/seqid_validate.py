"""
This script is intended to compare a fasta file containing influenza genome segments, extract a unique identifier, and compare its presence to that within a seperate a seperate dataframe. 
This script takes a fasta file in a strict header format "seqID_segment#"
"""

import argparse
from Bio import SeqIO
import pandas as pd
import os

def parse_fasta(fasta_file):
    seq_ids = set()
    for record in SeqIO.parse(fasta_file, "fasta"):
        seqid_segment = record.id
        seqid = seqid_segment.split('_')[0]  # Extract the seqid before the segment number
        seq_ids.add(seqid)
    return seq_ids

def parse_metadata(metadata_file):
    metadata_df = pd.read_csv(metadata_file, sep="\t")
    metadata_seq_ids = set(metadata_df['seqid'])
    return metadata_seq_ids, metadata_df

def write_files(directory, fasta_ids, metadata_ids, metadata_df):
    os.makedirs(directory, exist_ok=True)

    # Write all seqids in the FASTA file
    fasta_ids_df = pd.DataFrame(list(fasta_ids), columns=['seqid'])
    fasta_ids_df.to_csv(os.path.join(directory, 'fasta_ids.tsv'), sep="\t", index=False)

    # Write all seqids in the metadata file
    metadata_ids_df = pd.DataFrame(list(metadata_ids), columns=['seqid'])
    metadata_ids_df.to_csv(os.path.join(directory, 'metadata_ids.tsv'), sep="\t", index=False)

    # Write seqids present in both files
    intersect_ids = fasta_ids & metadata_ids
    intersect_ids_df = pd.DataFrame(list(intersect_ids), columns=['seqid'])
    intersect_ids_df.to_csv(os.path.join(directory, 'intersect.tsv'), sep="\t", index=False)

    # Write seqids only in the FASTA file
    fasta_only_ids = fasta_ids - metadata_ids
    fasta_only_ids_df = pd.DataFrame(list(fasta_only_ids), columns=['seqid'])
    fasta_only_ids_df.to_csv(os.path.join(directory, 'fasta_only.tsv'), sep="\t", index=False)

    # Write seqids only in the metadata file
    metadata_only_ids = metadata_ids - fasta_ids
    metadata_only_ids_df = pd.DataFrame(list(metadata_only_ids), columns=['seqid'])
    metadata_only_ids_df.to_csv(os.path.join(directory, 'metadata_only.tsv'), sep="\t", index=False)

def compare_ids(fasta_file, metadata_file, output_metadata_file=None, output_dir=None):
    fasta_ids = parse_fasta(fasta_file)
    metadata_ids, metadata_df = parse_metadata(metadata_file)

    # 1. Number of unique IDs in the fasta file
    num_unique_fasta_ids = len(fasta_ids)
    print(f"1. Number of unique IDs in the FASTA file: {num_unique_fasta_ids}")

    # 2. Number of unique seqids in the metadata file
    num_unique_metadata_ids = len(metadata_ids)
    print(f"2. Number of unique IDs in the metadata file: {num_unique_metadata_ids}")

    # 3. Number of unique seqids present in both files
    common_ids = fasta_ids & metadata_ids
    num_common_ids = len(common_ids)
    print(f"3. Number of unique IDs present in both files: {num_common_ids}")

    # 4. Number of unique seqids in the FASTA file but not in the metadata file
    fasta_only_ids = fasta_ids - metadata_ids
    num_fasta_only_ids = len(fasta_only_ids)
    print(f"4. Number of unique IDs in the FASTA file but not in the metadata file: {num_fasta_only_ids}")

    # 5. Number of unique seqids in the metadata file but not in the FASTA file
    metadata_only_ids = metadata_ids - fasta_ids
    num_metadata_only_ids = len(metadata_only_ids)
    print(f"5. Number of unique IDs in the metadata file but not in the FASTA file: {num_metadata_only_ids}")

    # 6. Unique sequence IDs in the fasta file - uncomment this if you want these ID printed to the console 
    #print(f"\nUnique sequence IDs in the FASTA file: {fasta_ids}")

    # 7. Unique sequence IDs in the metadata file - uncomment this if you want these ID printed to the console 
    #print(f"\nUnique sequence IDs in the metadata file: {metadata_ids}")

    # 8. Write out a new metadata.tsv file with only the rows containing seqIDs present in the FASTA file
    if output_metadata_file:
        filtered_metadata_df = metadata_df[metadata_df['seqid'].isin(fasta_ids)]
        filtered_metadata_df.to_csv(output_metadata_file, sep="\t", index=False)
        print(f"\nFiltered metadata written to: {output_metadata_file}")

    # 9. Write out the five specified files
    if output_dir:
        write_files(output_dir, fasta_ids, metadata_ids, metadata_df)
        print(f"\nFiles written to: {output_dir}")
        print("\nFiles created:")
        print("  fasta_ids.tsv: Contains all seqids present in the FASTA file.")
        print("  metadata_ids.tsv: Contains all seqids present in the metadata file.")
        print("  intersect.tsv: Contains seqids present in both the FASTA and metadata files.")
        print("  fasta_only.tsv: Contains seqids present only in the FASTA file.")
        print("  metadata_only.tsv: Contains seqids present only in the metadata file.")

def main():
    parser = argparse.ArgumentParser(description="Compare sequence IDs between a FASTA file and a metadata TSV file.")
    parser.add_argument('-f', '--fasta', required=True, help="Input FASTA file")
    parser.add_argument('-m', '--metadata', required=True, help="Input metadata TSV file")
    parser.add_argument('-o', '--output', help="Output metadata TSV file with only the rows containing seqIDs present in the FASTA file")
    parser.add_argument('-d', '--directory', help="Directory to write out 5 files containing the seqids for each of the metrics in the console (if not specified, files are written to the current directory). Files created:")
    
    args = parser.parse_args()
    
    compare_ids(args.fasta, args.metadata, args.output, args.directory)

if __name__ == "__main__":
    main()
