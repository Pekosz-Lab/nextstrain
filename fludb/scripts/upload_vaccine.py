"""
Requires a FASTA from GISAID with the following header format: Isolate name-Passage details/history | Isolate ID | Collection date | Passage details/history | Segment number  | Type | Lineage
Copy and paste this header format into the GISAID FASTA header field before downloading.
"""

import argparse
from Bio import SeqIO
import sqlite3

def format_date(date_str):
    """Format the collection date to YYYY-MM-DD or append Xs for incomplete dates."""
    if not date_str:
        return None
    date_parts = date_str.split('-')
    if len(date_parts) == 1:     # Only year
        return f"{date_parts[0]}-XX-XX"
    elif len(date_parts) == 2:  # Year and month
        return f"{date_parts[0]}-{date_parts[1]}-XX"
    elif len(date_parts) == 3:  # Full date
        return date_str
    else:
        return None  # If the date is in an unexpected format

def map_type_and_subtype(type_str, lineage_str):
    """Map the Type and Lineage to appropriate database values."""
    if "A_/_H1" in type_str and lineage_str == "pdm09":
        return "InfluenzaA", "H1N1"
    elif "A_/_H3" in type_str:
        return "InfluenzaA", "H3N2"
    elif "B" in type_str and lineage_str == "Victoria":
        return "InfluenzaB", "Victoria"
    elif "B" in type_str and lineage_str == "Yamagata":
        return "InfluenzaB", "Yamagata"
    else:
        return None, None

def update_database(db_path, fasta_file):
    # Define the segment mapping with normal GISAID IAV numbering
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

        if len(parts) < 7:
            print(f"Skipped record {header}: insufficient header parts.")
            fasta_records_skipped += 1
            continue

        sample_id = parts[0].strip()
        sequence_id = parts[1].strip()
        collection_date = format_date(parts[2].strip())
        passage_history = parts[3].strip()
        segment_num = parts[4].strip()
        type_str = parts[5].strip()
        lineage_str = parts[6].strip() if len(parts) > 6 else None

        segment_name = segment_map.get(segment_num)
        if not segment_name:
            print(f"Skipped record {header}: invalid segment number {segment_num}.")
            fasta_records_skipped += 1
            continue

        # Map type and subtype
        flu_type, subtype = map_type_and_subtype(type_str, lineage_str)
        if not flu_type or not subtype:
            print(f"Skipped record {header}: invalid type or lineage mapping.")
            fasta_records_skipped += 1
            continue

        sequence = str(record.seq)

        try:
            cursor.execute(f'''
                INSERT INTO influenza_genomes (sequence_ID, sample_ID, {segment_name}, date, passage_history, database_origin, type, subtype)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sequence_ID) DO UPDATE SET 
                    {segment_name} = excluded.{segment_name},
                    sample_ID = excluded.sample_ID,
                    date = excluded.date,
                    passage_history = excluded.passage_history,
                    database_origin = excluded.database_origin,
                    type = excluded.type,
                    subtype = excluded.subtype
            ''', (sequence_id, sample_id, sequence, collection_date, passage_history, database_origin, flu_type, subtype))
            fasta_records_inserted += 1
        except Exception as e:
            print(f"Skipped record {header}: {e}")
            fasta_records_skipped += 1

    print(f"FASTA file processed: {fasta_records_inserted} records inserted, {fasta_records_skipped} records skipped.")

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
    parser = argparse.ArgumentParser(description="Upload GISAID FASTA file to a SQLite database.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the GISAID FASTA file.')

    args = parser.parse_args()

    # Call the function with parsed arguments
    update_database(args.db, args.fasta)
