import argparse
from Bio import SeqIO
import pandas as pd
import sqlite3

def get_segment_map(influenza_type):
    """Return the segment map dynamically based on influenza type."""
    if influenza_type == "InfluenzaA":
        return {
            "1": "pb2", 
            "2": "pb1",
            "3": "pa",
            "4": "ha",
            "5": "np",
            "6": "na",
            "7": "mp",
            "8": "ns"
        }
    elif influenza_type == "InfluenzaB":
        return {
            "1": "pb1",  
            "2": "pb2",  
            "3": "pa",
            "4": "ha",
            "5": "np",
            "6": "na",
            "7": "mp",
            "8": "ns"
        }
    else:
        raise ValueError(f"Invalid influenza type '{influenza_type}'. Please make sure the type is either 'InfluenzaA' or 'InfluenzaB'.")

def update_database(db_path, fasta_file, metadata_file, require_sequence):
    """Update the SQLite database with sequences from the FASTA file and metadata."""
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("Database connection established.")

    # Set default values for database origin and location
    database_origin = "mostafa_lab"
    location = "JHH"

    # Load metadata and determine types dynamically for each sample
    metadata_df = pd.read_csv(metadata_file, sep='\t')
    if 'type' not in metadata_df.columns:
        raise ValueError("Metadata file must include the 'type' column.")
    
    # Parse the FASTA file
    print("Processing FASTA file...")
    fasta_count = 0
    skipped_fasta = 0

    for record in SeqIO.parse(fasta_file, "fasta"):
        header = record.id
        try:
            sequence_ID, segment_num = header.split("_")
            
            # Look up the influenza type for this sample from the metadata
            metadata_row = metadata_df[metadata_df['sequence_ID'] == sequence_ID]
            if metadata_row.empty:
                skipped_fasta += 1
                print(f"Skipping record {header}: No metadata found for sequence_ID {sequence_ID}.")
                continue

            # Extract influenza type for the current sequence
            influenza_type = metadata_row.iloc[0]['type']
            segment_map = get_segment_map(influenza_type)  # Get segment map dynamically based on type
            segment_name = segment_map.get(segment_num)

            if not segment_name:
                skipped_fasta += 1
                print(f"Skipping record {header}: No valid segment mapping found for segment number {segment_num}.")
                continue

            # Insert the sequence into the correct segment column
            sequence = str(record.seq)
            cursor.execute(f'''
                INSERT INTO influenza_genomes (sequence_ID, {segment_name}, location, database_origin)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sequence_ID) DO UPDATE SET 
                    {segment_name} = COALESCE(EXCLUDED.{segment_name}, {segment_name}),
                    location = COALESCE(EXCLUDED.location, location),
                    database_origin = COALESCE(EXCLUDED.database_origin, database_origin)
            ''', (sequence_ID, sequence, location, database_origin))
            fasta_count += 1

        except ValueError:
            skipped_fasta += 1

    print(f"FASTA file processed: {fasta_count} records inserted, {skipped_fasta} records skipped.")

    # Metadata population
    print("Processing metadata file...")
    metadata_count = 0
    skipped_metadata = 0

    for _, row in metadata_df.iterrows():
        sequence_ID = row['sequence_ID']
        sample_ID = row['sample_ID']
        sequencing_run = row['sequencing_run']
        date = row['date']
        passage_history = row['passage_history']
        type_ = row['type']
        subtype = row['subtype']

        # Check if sequence data exists for the current sequence_ID
        if require_sequence:
            cursor.execute('''
                SELECT COUNT(*) FROM influenza_genomes 
                WHERE sequence_ID = ? AND 
                      (pb2 IS NOT NULL OR pb1 IS NOT NULL OR pa IS NOT NULL OR 
                       ha IS NOT NULL OR np IS NOT NULL OR na IS NOT NULL OR 
                       mp IS NOT NULL OR ns IS NOT NULL)
            ''', (sequence_ID,))
            has_sequence_data = cursor.fetchone()[0] > 0

            if not has_sequence_data:
                skipped_metadata += 1
                continue

        cursor.execute('''
            INSERT INTO influenza_genomes (
                sequence_ID, sample_ID, sequencing_run, date, passage_history, type, subtype, location, database_origin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sequence_ID) DO UPDATE SET
                sample_ID = COALESCE(EXCLUDED.sample_ID, sample_ID),
                sequencing_run = COALESCE(EXCLUDED.sequencing_run, sequencing_run),
                date = COALESCE(EXCLUDED.date, date),
                passage_history = COALESCE(EXCLUDED.passage_history, passage_history),
                type = COALESCE(EXCLUDED.type, type),
                subtype = COALESCE(EXCLUDED.subtype, subtype),
                location = COALESCE(EXCLUDED.location, location),
                database_origin = COALESCE(EXCLUDED.database_origin, database_origin)
        ''', (sequence_ID, sample_ID, sequencing_run, date, passage_history, type_, subtype, location, database_origin))
        metadata_count += 1

    print(f"Metadata file processed: {metadata_count} records inserted or updated, {skipped_metadata} records skipped due to missing sequencing data.")

    # Commit changes and verify
    conn.commit()
    print("Data committed to the database. Verifying entries...")
    cursor.execute('SELECT COUNT(*) FROM influenza_genomes;')
    total_records = cursor.fetchone()[0]
    print(f"Total records in the database: {total_records}")

    # Close the connection
    conn.close()
    print("Database connection closed.")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Upload FASTA and metadata files to a SQLite database.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the FASTA file.')
    parser.add_argument('-m', '--metadata', required=True, help='Path to the metadata TSV file.')
    parser.add_argument('--require-sequence', action='store_true', help='Require at least one segment of sequencing data for metadata to be uploaded.')

    args = parser.parse_args()
    update_database(args.db, args.fasta, args.metadata, args.require_sequence)