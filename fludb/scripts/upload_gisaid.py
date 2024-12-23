import argparse
from Bio import SeqIO
import pandas as pd
import sqlite3

def format_date(date_str):
    """Format the collection date to YYYY-MM-DD or append Xs for incomplete dates."""
    if pd.isna(date_str):  # Handle NaT (Not a Time)
        return None
    date_parts = date_str.split('-')
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
    print("Database connection established.")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Populate database_origin value
    database_origin = 'gisaid'

    # Process the FASTA file
    print("Processing FASTA file...")
    fasta_records_inserted = 0
    fasta_records_skipped = 0

    for record in SeqIO.parse(fasta_file, "fasta"):
        header = record.id
        parts = header.split("|")  # Split by '|'

        isolate_name = parts[0].strip()
        collection_date = parts[1].strip()
        passage_history = parts[2].strip()
        segment_num = parts[3].strip()
        isolate_id = parts[4].strip() if len(parts) > 4 else None

        segment_name = segment_map.get(segment_num)
        sequence = str(record.seq)

        try:
            cursor.execute(f'''
                INSERT INTO influenza_genomes (sequence_ID, sample_ID, {segment_name}, database_origin)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sequence_ID) DO UPDATE SET {segment_name} = ?, sample_ID = ?, database_origin = ?
            ''', (isolate_id, isolate_name, sequence, database_origin, sequence, isolate_name, database_origin))
            fasta_records_inserted += 1
        except Exception as e:
            print(f"Skipped record {header}: {e}")
            fasta_records_skipped += 1

    print(f"FASTA file processed: {fasta_records_inserted} records inserted, {fasta_records_skipped} records skipped.")

    # Process the metadata file
    print("Processing metadata file...")
    metadata_records_inserted = 0
    metadata_records_skipped = 0
    metadata_df = pd.read_excel(metadata_file)

    for _, row in metadata_df.iterrows():
        seq_id = row['Isolate_Id']
        isolate_name = row.get('Isolate_Name', None)
        lineage = row.get('Lineage', None)
        collection_date = format_date(row.get('Collection_Date', None))
        passage_history = row.get('Passage_History', None)
        location = row.get('Location', None)
        age = row.get('Host_Age', None)
        age_unit = row.get('Host_Age_Unit', None)
        sex = row.get('Host_Gender', None)

        try:
            cursor.execute('''
                INSERT INTO influenza_genomes (sequence_ID, sample_ID, subtype, date, passage_history, location, database_origin, age, age_unit, sex)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sequence_ID) DO UPDATE SET
                    sample_ID = COALESCE(?, sample_ID),
                    subtype = COALESCE(?, subtype),
                    date = COALESCE(?, date),
                    passage_history = COALESCE(?, passage_history),
                    location = COALESCE(?, location),
                    database_origin = COALESCE(?, database_origin),
                    age = COALESCE(?, age),
                    age_unit = COALESCE(?, age_unit),
                    sex = COALESCE(?, sex)
            ''', (seq_id, isolate_name, lineage, collection_date, passage_history, location, database_origin, age, age_unit, sex,
                  isolate_name, lineage, collection_date, passage_history, location, database_origin, age, age_unit, sex))
            metadata_records_inserted += 1
        except Exception as e:
            print(f"Skipped record {seq_id}: {e}")
            metadata_records_skipped += 1

    print(f"Metadata file processed: {metadata_records_inserted} records inserted or updated, "
          f"{metadata_records_skipped} records skipped due to missing sequencing data.")

    # Commit changes and verify total records
    conn.commit()
    print("Data committed to the database. Verifying entries...")

    cursor.execute("SELECT COUNT(*) FROM influenza_genomes")
    total_records = cursor.fetchone()[0]
    print(f"Total records in the database: {total_records}")

    # Close the database connection
    conn.close()
    print("Database connection closed.")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Upload GISAID FASTA and metadata files to a SQLite database.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the GISAID FASTA file.')
    parser.add_argument('-m', '--metadata', required=True, help='Path to the GISAID metadata XLS file.')

    args = parser.parse_args()
    
    # Call the function with parsed arguments
    update_database(args.db, args.fasta, args.metadata)
