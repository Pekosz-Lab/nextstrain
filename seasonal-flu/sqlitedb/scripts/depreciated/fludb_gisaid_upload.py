import argparse
from Bio import SeqIO
import pandas as pd
import sqlite3

def format_date(date_str):
    """Format the collection date to YYYY-MM-DD or append Xs for incomplete dates."""
    if pd.isna(date_str):  # Handle NaT (Not a Time)
        return None
    date_parts = date_str.split('-')
    
    # Determine the number of parts and format accordingly
    if len(date_parts) == 1:  # Only year
        return f"{date_parts[0]}-XX-XX"
    elif len(date_parts) == 2:  # Year and month
        return f"{date_parts[0]}-{date_parts[1]}-XX"
    elif len(date_parts) == 3:  # Full date
        return date_str
    else:
        return None  # If the date is in an unexpected format

def update_database(db_path, fasta_file, metadata_file):
    # Define the segment mapping
    segment_map = {
        "1": "pb1",
        "2": "pb2",
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

    # Populate database_origin value
    database_origin = 'gisaid'

    # Parse and update the database with sequences from the FASTA file
    for record in SeqIO.parse(fasta_file, "fasta"):
        # Extract the header and split it
        header = record.id
        parts = header.split("|")  # Split by '|'
        
        # Assign the isolate_name from the header and segment number
        isolate_name = parts[0].strip()  # Isolate name
        collection_date = parts[1].strip()  # Collection date
        passage_history = parts[2].strip()  # Passage details/history
        segment_num = parts[3].strip()  # Segment number
        isolate_id = parts[4].strip() if len(parts) > 4 else None  # Isolate_ID

        # Convert segment number to segment name
        segment_name = segment_map.get(segment_num)

        # Prepare the sequence data
        sequence = str(record.seq)
        
        # Update the database with sequence data
        cursor.execute(f'''
            INSERT INTO influenza_genomes (seq_id, sample_id, {segment_name}, database_origin)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(seq_id) DO UPDATE SET {segment_name} = ?, sample_id = ?, database_origin = ?
        ''', (isolate_id, isolate_name, sequence, database_origin, sequence, isolate_name, database_origin))

    # Load and update the database with metadata from the XLS file
    metadata_df = pd.read_excel(metadata_file)  # Read .xls file

    for _, row in metadata_df.iterrows():
        seq_id = row['Isolate_Id']  # This is the seq_id
        isolate_name = row.get('Isolate_Name', None)  # Use None if field is missing
        subtype = row.get('Subtype', None)  # Use None if field is missing
        
        # Format collection date
        collection_date = format_date(row.get('Collection_Date', None))
        
        passage_history = row.get('Passage_History', None)
        study_id = row.get('Submitting_Sample_Id', None)
        location = row.get('Location', None)  # Extract the location from the metadata
        
        # Update the database with metadata
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
        ''', (seq_id, isolate_name, subtype, collection_date, passage_history, study_id, location, database_origin,
              isolate_name, subtype, collection_date, passage_history, study_id, location, database_origin))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Upload GISAID FASTA and metadata files to a SQLite database.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the GISAID FASTA file.')
    parser.add_argument('-m', '--metadata', required=True, help='Path to the GISAID metadata XLS file.')

    args = parser.parse_args()
    
    # Call the function with parsed arguments
    update_database(args.db, args.fasta, args.metadata)