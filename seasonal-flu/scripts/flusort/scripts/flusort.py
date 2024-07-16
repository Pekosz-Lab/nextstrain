import os
import argparse
import pandas as pd
from Bio import SeqIO
from Bio.Blast.Applications import NcbiblastnCommandline
import re
import subprocess
import shutil

def parse_fasta_file(fasta_file):
    sequence_data = {}

    with open(fasta_file, "r") as file:
        for record in SeqIO.parse(file, "fasta"):
            sequence_id = record.id
            sequence_data[sequence_id] = []

            print(f"Fasta File: {fasta_file}, Sequence Header: {sequence_id}")

    return sequence_data 

blast_cmd = []

def run_blast(input_fasta, custom_blast_db, blast_output_file):
    # Construct the BLAST command
    global blast_cmd  # Use the global variable
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

    # Run the BLAST 
    try:
        result = subprocess.check_output(blast_cmd, stderr=subprocess.STDOUT, text=True)
        print(result)
    except subprocess.CalledProcessError as e:
        print(f"Error running BLAST: {e.output}")

    print(f"BLAST search completed. Results saved to {blast_output_file}")

def write_no_hits_sequences(input_fasta, blast_output_file, no_hits_output_file):
    # Get the sequence IDs with BLAST hits
    sequences_with_hits = set(parse_blast_output(blast_output_file).keys())

    # Write sequences without hits to a new FASTA file
    records = list(SeqIO.parse(input_fasta, "fasta"))
    no_hits_records = [record for record in records if record.id not in sequences_with_hits]

    with open(no_hits_output_file, "w") as output_handle:
        SeqIO.write(no_hits_records, output_handle, "fasta")

    print(f"Sequences without BLAST hits written to: {no_hits_output_file}")

    # Run BLAST 
    subprocess.run(blast_cmd)

def append_subtype_to_headers(input_fasta, output_fasta, grouped_df, delimiter="|"):
    """
    Append subtype information to sequence headers in the FASTA file using a specified delimiter.

    Args:
        input_fasta (str): Path to the input FASTA file.
        output_fasta (str): Path to the output FASTA file with updated headers.
        grouped_df (pd.DataFrame): DataFrame containing subtype information.
        delimiter (str): Delimiter to use in the sequence headers. Defaults to '|' but can be switched to "_" or any delimiter chosen.
        
        new_header = f"{sequence_id}_{segment_number}{virus_type_suffix}{subtype}{delimiter}{completeness}"
        
        seqID and segment number are rejoined to the original sequence sequence identifier independent of the specified new delimiter in order to maintain compatability with augur and external records.
        
        
    """
    records = list(SeqIO.parse(input_fasta, "fasta"))
    modified_records = []

    for record in records:
        sequence_id, segment_number = record.id.split("_")

        if sequence_id in grouped_df['Sequence_ID'].values:
            row = grouped_df[grouped_df['Sequence_ID'] == sequence_id].iloc[0]

            ha_subtype = row['H_Subtype']
            na_subtype = row['N_Subtype']

            subtype = f"{delimiter}{ha_subtype}{delimiter}{na_subtype}" if ha_subtype and na_subtype else ""
            virus_type = row['Virus_Type']
            virus_type_suffix = f"{virus_type}" if virus_type else ""
            completeness = row['Completeness']

            new_header = f"{sequence_id}_{segment_number}{delimiter}{sequence_id}{delimiter}{segment_number}{delimiter}{virus_type_suffix}{subtype}{delimiter}{completeness}"

            record.id = new_header
            record.description = ""

            print(f"Updated Sequence Header: {record.id}")

        modified_records.append(record)

    with open(output_fasta, "w") as output_handle:
        SeqIO.write(modified_records, output_handle, "fasta")

'''
def parse_blast_output(blast_output_file):
    sequence_ids = {}

    with open(blast_output_file, "r") as blast_file:
        for line in blast_file:
            fields = line.strip().split("\t")
            if len(fields) >= 2:
                query_id = fields[0]
                sseqid = fields[1].split()[0]
                sequence_ids[query_id] = sseqid

    return sequence_ids
'''

def parse_blast_output(blast_output_file):
    # Read the BLAST output into a DataFrame
    blast_df = pd.read_csv(blast_output_file, sep='\t', header=None, names=['query_id', 'sseqid', 'qlen', 'slen', 'evalue', 'bitscore'])

    # Convert bitscore column to numeric
    blast_df['bitscore'] = pd.to_numeric(blast_df['bitscore'], errors='coerce')

    # Filter to keep only rows with the highest bitscore for each query ID
    filtered_blast_df = blast_df.loc[blast_df.groupby('query_id')['bitscore'].idxmax()]

    sequence_ids = dict(zip(filtered_blast_df['query_id'], filtered_blast_df['sseqid']))

    return sequence_ids


def split_appended_name(appended_name):
    match = re.match(r"(.*?_\d+)(_A-seg\d+|_B-seg\d+)(_N\d+|_H\d+)?", appended_name)
    if match:
        sequence_id = match.group(1)
        segment_number = match.group(2)
        subtype = match.group(3) if match.group(3) else ""
        return sequence_id, segment_number, subtype
    else:
        return None, None, None

def main():
    parser = argparse.ArgumentParser(description="Perform BLAST searches on FASTA sequences.")
    parser.add_argument("-i", "--input_file", required=True, help="Path to the input FASTA file.")
    parser.add_argument("-db", "--blast_db", help="Path to the custom BLAST database file.")
    parser.add_argument("-o", "--output_directory", help="Path to the output directory. Defaults to 'flusort_out' in the script's directory.")
    parser.add_argument("-d", "--delimiter", default="|", help="Delimiter to use in the FASTA headers. Defaults to '|'.")
    args = parser.parse_args()

    output_directory = args.output_directory or os.path.join(os.path.dirname(os.path.abspath(__file__)), "flusort_out")
    os.makedirs(output_directory, exist_ok=True)

    pd.set_option('display.max_rows', None)

    custom_blast_db = args.blast_db or "./blast_database/pyflute_ha_database"

    blast_output_file = os.path.join(output_directory, 'blast_output.txt')
    run_blast(args.input_file, custom_blast_db, blast_output_file)

    no_hits_output_file = os.path.join(output_directory, 'sequences_without_hits.fasta')
    write_no_hits_sequences(args.input_file, blast_output_file, no_hits_output_file)

    sequence_ids = parse_blast_output(blast_output_file)

    data = []

    records = list(SeqIO.parse(args.input_file, "fasta"))
    for record in records:
        sequence_id = record.id
        sseqid = sequence_ids.get(sequence_id)
        if sseqid:
            record.id = f"{record.id}_{sseqid}"
            record.description = ""

            sequence_id, segment_number, subtype = split_appended_name(record.id)

            print(f"Updated Sequence Header: {record.id}")

            data.append({"Sequence_ID": re.sub(r"_\d+$", "", sequence_id), "Segment_Number": segment_number.replace("_", ""), "Subtype": subtype.replace("_", "")})

    df = pd.DataFrame(data)

    df.to_csv(os.path.join(output_directory, 'original_dataframe.csv'), index=False)

    print("\nOriginal DataFrame:")
    print(df)

    grouped_df = df.groupby('Sequence_ID').agg({
        'Segment_Number': ', '.join,
        'Subtype': lambda x: ', '.join(sorted(set(x))),
    }).reset_index()

    grouped_df['Virus_Type'] = grouped_df['Segment_Number'].apply(lambda x: 'InfluenzaA' if re.search(r'A-seg\d+', x) else 'InfluenzaB' if re.search(r'B-seg\d+', x) else 'Unknown')
    grouped_df['H_Subtype'] = grouped_df['Subtype'].apply(lambda x: ', '.join([subtype for subtype in x.split(', ') if 'H' in subtype]))
    grouped_df['N_Subtype'] = grouped_df['Subtype'].apply(lambda x: ', '.join([subtype for subtype in x.split(', ') if 'N' in subtype]))

    grouped_df['Completeness'] = grouped_df['Segment_Number'].apply(lambda x: 'Complete' if len(x.split(', ')) == 8 else 'Incomplete')

    grouped_df.drop(columns=['Subtype'], inplace=True)

    grouped_df['H_Subtype'].replace('', 'undetermined-HA', inplace=True)
    grouped_df['N_Subtype'].replace('', 'undetermined-NA', inplace=True)

    grouped_df.to_csv(os.path.join(output_directory, 'grouped_dataframe.csv'), index=False)

    print("\nGrouped DataFrame:")
    print(grouped_df)

    pd.reset_option('display.max_rows')

    output_fasta_file = os.path.join(output_directory, 'fasta_with_subtype.fasta')
    append_subtype_to_headers(args.input_file, output_fasta_file, grouped_df, delimiter=args.delimiter)

if __name__ == "__main__":
    main()
