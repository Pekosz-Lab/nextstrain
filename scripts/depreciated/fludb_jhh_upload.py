import argparse
from Bio import SeqIO
import pandas as pd
import sqlite3

def update_database(db_path, fasta_file, metadata_file):
    # Define the segment mapping
    segment_map = {
        "1": "pb2", 
        "2": "pb1",
        "3": "pa",
        "4": "ha",
        "5": "np",
        "6": "na",
        "7": "mp",
        "8": "ns"
    }

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Set default values for database origin and location
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
        
        # Update the database with sequence data, location, and database_origin
        cursor.execute(f'''
            INSERT INTO influenza_genomes (seq_id, subtype, {segment_name}, location, database_origin)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(seq_id) DO UPDATE SET 
                {segment_name} = ?, 
                subtype = COALESCE(?, subtype),
                location = COALESCE(?, location),
                database_origin = COALESCE(?, database_origin)
        ''', (seq_id, subtype, sequence, location, database_origin, sequence, subtype, location, database_origin))

    # Load and update the database with metadata from the TSV file
    metadata_df = pd.read_csv(metadata_file, sep='\t')

    for _, row in metadata_df.iterrows():
        seq_id = row['seqid']
        sample_id = row.get('sample_id', None)  # Use None if field is missing
        subtype = row.get('subtype', None)      # Use None if field is missing
        collection_date = row.get('collection_date', None)
        passage_history = row.get('passage_history', None)
        study_id = row.get('study_id', None)
        
        # Update the database with metadata, location, and database_origin
        cursor.execute('''
            INSERT INTO influenza_genomes (seq_id, sample_id, subtype, collection_date, passage_history, study_id, location, database_origin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(seq_id) DO UPDATE SET
                sample_id = COALESCE(?, sample_id),
                subtype = COALESCE(?, subtype),
                collection_date = COALESCE(?, collection_date),
                passage_history = COALESCE(?, passage_history),
                study_id = COALESCE(?, study_id),
                location = COALESCE(?, location),
                database_origin = COALESCE(?, database_origin)
        ''', (seq_id, sample_id, subtype, collection_date, passage_history, study_id, location, database_origin,
              sample_id, subtype, collection_date, passage_history, study_id, location, database_origin))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Upload FASTA and metadata files to a SQLite database.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the FASTA file.')
    parser.add_argument('-m', '--metadata', required=True, help='Path to the metadata TSV file.')

    args = parser.parse_args()
    
    # Call the function with parsed arguments
    update_database(args.db, args.fasta, args.metadata)