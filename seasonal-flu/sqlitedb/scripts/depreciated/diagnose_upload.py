# upload diagnostic 

import sqlite3
from Bio import SeqIO

def get_segment_map(influenza_type):
    """Return the segment map based on influenza type."""
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
            "1": "pb1",  # NCBI IBV segment number places PB1 as "segment 1".
            "2": "pb2",  # Flipped compared to the canonical segment mapping.
            "3": "pa",
            "4": "ha",
            "5": "np",
            "6": "na",
            "7": "mp",
            "8": "ns"
        }
    else:
        raise ValueError(f"Invalid influenza type '{influenza_type}'. Please make sure the type is either 'InfluenzaA' or 'InfluenzaB'.")

def diagnose_fasta(fasta_file, influenza_type, database_path):
    """Diagnose issues in the FASTA file processing and segment mapping."""
    
    # Connect to the database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Get the segment map for the specified influenza type
    segment_map = get_segment_map(influenza_type)
    print(f"Using segment map for {influenza_type}: {segment_map}")

    # Counters for the FASTA file
    fasta_count = 0
    skipped_fasta = 0

    # Open the FASTA file and process each record
    for record in SeqIO.parse(fasta_file, "fasta"):
        header = record.id
        try:
            # Parse the sequence ID and segment number from the header
            sequence_ID, segment_num = header.split("_")
            segment_name = segment_map.get(segment_num)

            # If no segment is found for this segment number, skip
            if not segment_name:
                skipped_fasta += 1
                print(f"Skipping record {header}: No valid segment mapping found for segment number {segment_num}.")
                continue

            # Debugging output for each record
            print(f"Parsed header {header} -> Segment number: {segment_num}, Mapped to: {segment_name}")

            # Insert the sequence into the database
            sequence = str(record.seq)
            cursor.execute(f'''
                INSERT INTO influenza_genomes (sequence_ID, {segment_name}, location, database_origin)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sequence_ID) DO UPDATE SET 
                    {segment_name} = COALESCE(EXCLUDED.{segment_name}, {segment_name}),
                    location = COALESCE(EXCLUDED.location, location),
                    database_origin = COALESCE(EXCLUDED.database_origin, database_origin)
            ''', (sequence_ID, sequence, 'unknown_location', 'unknown_origin'))
            fasta_count += 1

        except ValueError as e:
            # Handle parsing errors (e.g., incorrect header format)
            skipped_fasta += 1
            print(f"Error processing header {header}: {e}")

    # Final summary
    print(f"\nProcessing complete. Total records processed: {fasta_count}")
    print(f"Skipped records: {skipped_fasta}")
    conn.commit()
    conn.close()

# Example usage of the script
fasta_file = "results/out.fasta"  # Replace with your FASTA file path
influenza_type = "InfluenzaA"  # or "InfluenzaA"
database_path = "fludb.db"  # Replace with your actual database file path

diagnose_fasta(fasta_file, influenza_type, database_path)
