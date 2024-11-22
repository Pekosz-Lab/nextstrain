import argparse
from Bio import SeqIO
import pandas as pd
import sqlite3
import logging

def update_database(db_path, fasta_file, metadata_file, log_file):
    # Define the segment mapping specific to IBV
    segment_map = {
        "1": "pb1",  # NCBI IBV segment number places PB1 as "segment 1".
        "2": "pb2",  # Flipped compared to the canonical segment mapping.
        "3": "pa",
        "4": "ha",
        "5": "np",
        "6": "na",
        "7": "mp",
        "8": "ns"
    }

    # Set up logging to log skipped entries
    logging.basicConfig(filename=log_file, level=logging.WARNING, 
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Set database origin and location for all entries
    database_origin = "mostafa_lab"
    location = "JHH"

    # Parse and update the database with sequences from the FASTA file
    for record in SeqIO.parse(fasta_file, "fasta"):
        # Extract the seq_id and segment number
        header = record.id
        seq_id, segment_num = header.split("_")

        # Convert segment number to segment name
        segment_name = segment_map.get(segment_num)
        
        # Prepare the sequence data
        sequence = str(record.seq)
        
        # Set subtype to NULL if not provided
        subtype = None

        # Update the database with sequence data
        cursor.execute(f'''
            INSERT INTO influenza_genomes (seq_id, subtype, {segment_name}, database_origin, location)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(seq_id) DO UPDATE SET {segment_name} = ?, subtype = ?, database_origin = ?, location = ?
        ''', (seq_id, subtype, sequence, database_origin, location, sequence, subtype, database_origin, location))

    # Load and update the database with metadata from the TSV file
    metadata_df = pd.read_csv(metadata_file, sep='\t')

    skipped_seq_ids = []

    for _, row in metadata_df.iterrows():
        seq_id = row['seqid']
        sample_id = row.get('sample_id', None)  # Use None if field is missing
        subtype = row.get('subtype', None)      # Use None if field is missing
        collection_date = row.get('collection_date', None)
        passage_history = row.get('passage_history', None)
        study_id = row.get('study_id', None)
        sequencing_run = row.get('sequencing_run', None)

        # Check if at least one segment sequence is present for this seq_id
        cursor.execute('''
            SELECT pb1, pb2, pa, ha, np, na, mp, ns
            FROM influenza_genomes
            WHERE seq_id = ?
        ''', (seq_id,))
        
        result = cursor.fetchone()

        # If result is None, no segments are found for this seq_id
        if result is None or not any(result):
            skipped_seq_ids.append(seq_id)
            logging.warning(f"Skipped metadata for seq_id {seq_id} - No segment data found.")
            print(f"WARNING: Skipped metadata for seq_id {seq_id}. No segment data found.")
            continue

        # Update the database with metadata
        cursor.execute('''
            INSERT INTO influenza_genomes (seq_id, sample_id, subtype, collection_date, passage_history, study_id, sequencing_run, database_origin, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(seq_id) DO UPDATE SET
                sample_id = COALESCE(?, sample_id),
                subtype = COALESCE(?, subtype),
                collection_date = COALESCE(?, collection_date),
                passage_history = COALESCE(?, passage_history),
                study_id = COALESCE(?, study_id),
                sequencing_run = COALESCE(?, sequencing_run),
                database_origin = COALESCE(?, database_origin),
                location = COALESCE(?, location)
        ''', (seq_id, sample_id, subtype, collection_date, passage_history, study_id, sequencing_run, database_origin, location,
              sample_id, subtype, collection_date, passage_history, study_id, sequencing_run, database_origin, location))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # Log a summary of skipped seq_ids
    if skipped_seq_ids:
        print(f"WARNING: {len(skipped_seq_ids)} sequences were skipped due to missing segment data. Check {log_file} for details.")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Upload FASTA and metadata files to a SQLite database.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the FASTA file.')
    parser.add_argument('-m', '--metadata', required=True, help='Path to the metadata TSV file.')
    parser.add_argument('-l', '--log', required=False, default='upload_log.txt', help='Path to the log file for skipped entries.')

    args = parser.parse_args()

    # Call the function with parsed arguments
    update_database(args.db, args.fasta, args.metadata, args.log)