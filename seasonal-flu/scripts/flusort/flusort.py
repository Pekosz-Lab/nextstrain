import os
import argparse
import pandas as pd
from Bio import SeqIO
import subprocess
import re
import shutil 

def parse_fasta_file(fasta_file):
    sequence_data = {}
    with open(fasta_file, "r") as file:
        for record in SeqIO.parse(file, "fasta"):
            sequence_id = record.id
            sequence_data[sequence_id] = []
    return sequence_data

def split_appended_name(appended_name):
    match = re.match(r"(.*?_\d+)(_A-seg\d+|_B-seg\d+)(_N\d+|_H\d+)?", appended_name)
    if match:
        sequence_id = match.group(1)
        segment_number = match.group(2)
        subtype = match.group(3) if match.group(3) else ""
        return sequence_id, segment_number, subtype
    else:
        return None, None, None

def run_blast(input_fasta, custom_blast_db, blast_output_file):
    blast_cmd = [
        "blastn",
        "-query", input_fasta,
        "-db", custom_blast_db,
        "-out", blast_output_file,
        "-word_size", "11",
        "-num_threads", "8",
        "-outfmt", "6 qseqid sseqid qlen slen evalue bitscore",
        "-evalue", "20"
    ]
    try:
        result = subprocess.check_output(blast_cmd, stderr=subprocess.STDOUT, text=True)
        print(result)
    except subprocess.CalledProcessError as e:
        print(f"❌Error running BLAST: {e.output}")
    print("🚀 BLAST+ search completed.")
    print(f"🚀 BLAST+ output written to {blast_output_file}")
    print("💭 Use --out_BLAST_no_hits to show sequences with no hits.")

def write_fasta_with_subtypes(input_fasta, output_fasta, grouped_df, delimiter="|"):
    records = list(SeqIO.parse(input_fasta, "fasta"))
    modified_records = []
    for record in records:
        sequence_id, segment_number = record.id.split("_")
        if sequence_id in grouped_df['sequence_ID'].values:
            row = grouped_df[grouped_df['sequence_ID'] == sequence_id].iloc[0]
            ha_subtype = row['H_Subtype']
            na_subtype = row['N_Subtype']
            subtype = f"{delimiter}{ha_subtype}{delimiter}{na_subtype}" if ha_subtype and na_subtype else ""
            type = row['type']
            type_suffix = f"{type}" if type else ""
            completeness = row['Completeness']
            new_header = f"{sequence_id}_{segment_number}{delimiter}{sequence_id}{delimiter}{segment_number}{delimiter}{type_suffix}{subtype}{delimiter}{completeness}"
            record.id = new_header
            record.description = ""
        modified_records.append(record)
    with open(output_fasta, "w") as output_handle:
        SeqIO.write(modified_records, output_handle, "fasta")

def copy_fasta(input_fasta, output_fasta):
    """ Copies the original input FASTA to the output path without modification. """
    shutil.copy(input_fasta, output_fasta)

def parse_blast_output(blast_output_file):
    blast_df = pd.read_csv(blast_output_file, sep='\t', header=None, names=['query_id', 'sseqid', 'qlen', 'slen', 'evalue', 'bitscore'])
    blast_df['bitscore'] = pd.to_numeric(blast_df['bitscore'], errors='coerce')
    filtered_blast_df = blast_df.loc[blast_df.groupby('query_id')['bitscore'].idxmax()]
    sequence_ids = dict(zip(filtered_blast_df['query_id'], filtered_blast_df['sseqid']))
    return sequence_ids

def main():
    parser = argparse.ArgumentParser(description="Perform BLAST searches on FASTA sequences.")
    parser.add_argument("-i", "--input_file", required=True, help="Path to the input FASTA file.")
    parser.add_argument("-db", "--blast_db", help="Path to the custom BLAST database file.")
    parser.add_argument("-m", "--metadata", required=True, help="Path to the metadata file (CSV or TSV).")

    # Flags for output files
    parser.add_argument("-f", "--out_original_fasta", required=True, help="Path to save the original FASTA file with subtype info.")
    parser.add_argument("-o", "--out_fludb", required=True, help="Path to save the fludb metadata results.")
    parser.add_argument("--out_grouped", nargs='?', help="Path to save the grouped results. Optional.")
    parser.add_argument("--out_subtype_fasta", nargs='?', help="Path to save the FASTA file with subtype information. Optional.")
    parser.add_argument("--out_BLAST_no_hits", nargs='?', help="Path to save sequences which did NOT RETURN BLAST hits. Optional.")
    parser.add_argument("-O", "--output_dir", help="Directory to save BLAST+ output file (if specified). Optional.")

    args = parser.parse_args()

    # Determine output directory
    output_directory = args.output_dir if args.output_dir else os.path.join(os.path.dirname(os.path.abspath(__file__)), "flusort_out")
    
    os.makedirs(output_directory, exist_ok=True)

    # Run BLAST
    print(f"🚀 Assigning Influenza type and subtypes by BLAST+")
    custom_blast_db = args.blast_db or "./blast_database/pyflute_ha_database"
    blast_output_file = os.path.join(output_directory, 'blast_output.txt')
    run_blast(args.input_file, custom_blast_db, blast_output_file)
    
    sequence_ids = parse_blast_output(blast_output_file)

    # Load input metadata
    input_metadata = pd.read_csv(args.metadata, sep='\t')

    # Process FASTA file
    data = []
    records = list(SeqIO.parse(args.input_file, "fasta"))
    for record in records:
        sequence_id = record.id
        sseqid = sequence_ids.get(sequence_id)
        if sseqid:
            record.id = f"{record.id}_{sseqid}"
            record.description = ""

            sequence_id, segment_number, subtype = split_appended_name(record.id)
            data.append({"sequence_ID": re.sub(r"_\d+$", "", sequence_id), "Segment_Number": segment_number.replace("_", ""), "Subtype": subtype.replace("_", "")})

    df = pd.DataFrame(data)
    grouped_df = df.groupby('sequence_ID').agg({
        'Segment_Number': ', '.join,
        'Subtype': lambda x: ', '.join(sorted(set(x))),
    }).reset_index()

    grouped_df['type'] = grouped_df['Segment_Number'].apply(
        lambda x: 'InfluenzaA' if re.search(r'A-seg\d+', x) else 'InfluenzaB' if re.search(r'B-seg\d+', x) else 'Unknown'
    )
    grouped_df['H_Subtype'] = grouped_df['Subtype'].apply(
        lambda x: ', '.join([subtype for subtype in x.split(', ') if 'H' in subtype])
    )
    grouped_df['N_Subtype'] = grouped_df['Subtype'].apply(
        lambda x: ', '.join([subtype for subtype in x.split(', ') if 'N' in subtype])
    )

    grouped_df['Completeness'] = grouped_df['Segment_Number'].apply(
        lambda x: 'Complete' if len(x.split(', ')) == 8 else 'Incomplete'
    )

    grouped_df['H_Subtype'].replace('', 'xx', inplace=True)
    grouped_df['N_Subtype'].replace('', 'xx', inplace=True)
    grouped_df['subtype'] = grouped_df['H_Subtype'] + grouped_df['N_Subtype']
    grouped_df.loc[grouped_df['type'] == 'InfluenzaB', 'subtype'] = 'Victoria'

    fludb_meta = grouped_df.drop(columns=['Segment_Number', 'Subtype', 'H_Subtype', 'N_Subtype', 'Completeness'])

    # Merge input metadata with fludb_meta
    merged_df = input_metadata.merge(fludb_meta, on='sequence_ID', how='left')

    # Copy the original FASTA file without modifications
    copy_fasta(args.input_file, args.out_original_fasta)

    # Save fludb metadata
    merged_df.to_csv(args.out_fludb, sep='\t', index=False)
    print(f"✅ Metadata with assigned types and subtypes saved to: {args.out_fludb}")

    if args.out_grouped:
        grouped_df.to_csv(args.out_grouped, sep='\t', index=False)
        print(f"Grouped dataframe saved to: {args.out_grouped}")

    # Optionally, save additional files
    if args.out_subtype_fasta:
        write_fasta_with_subtypes(args.input_file, args.out_subtype_fasta, grouped_df)
    if args.out_BLAST_no_hits:
        write_no_hits_sequences(args.input_file, blast_output_file, args.out_BLAST_no_hits)

if __name__ == "__main__":
    main()
