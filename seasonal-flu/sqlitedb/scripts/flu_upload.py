import sqlite3
import pandas as pd
from Bio import SeqIO

TODO: #fix sqlite3.OperationalError: near ",": syntax error 

def upload_sequences(fasta_file, conn):
    """Upload sequences from a FASTA file into the sequences table."""
    cursor = conn.cursor()

    # Map segment numbers to column names
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

    for record in SeqIO.parse(fasta_file, "fasta"):
        # Parse the header to get sequence ID and segment
        header = record.id
        sequence_id, segment = header.split('_')

        # Get the column name for the segment
        column_name = segment_map.get(segment)
        if column_name is None:
            print(f"Unknown segment {segment} for sequence {sequence_id}")
            continue

        # Check if the sequence_id already exists
        cursor.execute('SELECT * FROM sequences WHERE sequence_id = ?', (sequence_id,))
        row = cursor.fetchone()

        if row:
            # Update the existing row with the new segment data
            cursor.execute(f'''
            UPDATE sequences SET {column_name} = ? WHERE sequence_id = ?
            ''', (str(record.seq), sequence_id))
        else:
            # Insert a new row with NULLs for other columns
            cursor.execute(f'''
            INSERT INTO sequences (sequence_id, {column_name}) VALUES (?, ?)
            ''', (sequence_id, str(record.seq)))
            # Ensure all columns are initialized
            columns = ', '.join(segment_map.values())
            cursor.execute(f'''
            UPDATE sequences SET {columns} = {columns} WHERE sequence_id = ?
            ''', (sequence_id,))

    conn.commit()
    print("Sequences uploaded successfully.")

def upload_metadata(metadata_file, conn):
    """Upload metadata from a CSV file into the metadata tables."""
    cursor = conn.cursor()

    # Read the metadata CSV file
    metadata_df = pd.read_csv(metadata_file)

    # Determine which metadata table the columns belong to
    flusort_columns = ['sequence_id', 'type', 'ha_subtype', 'na_subtype', 'genome_completeness']
    mostafa_columns = ['sequence_id', 'deidentified_id', 'run_id', 'date_sequenced']

    flusort_data = metadata_df.loc[:, metadata_df.columns.isin(flusort_columns)]
    mostafa_data = metadata_df.loc[:, metadata_df.columns.isin(mostafa_columns)]

    # Upload metadata to metadata_flusort table
    if not flusort_data.empty:
        flusort_data.to_sql('metadata_flusort', conn, if_exists='append', index=False)

    # Upload metadata to metadata_mostafa table
    if not mostafa_data.empty:
        mostafa_data.to_sql('metadata_mostafa', conn, if_exists='append', index=False)

    conn.commit()
    print("Metadata uploaded successfully.")

def main(fasta_file, metadata_file=None):
    # Connect to the database
    conn = sqlite3.connect('sqlitedb/flu.db')

    # Upload sequences
    upload_sequences(fasta_file, conn)

    # Upload metadata if provided
    if metadata_file:
        upload_metadata(metadata_file, conn)

    # Close the connection
    conn.close()
    print("Database operations completed successfully.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Upload sequences and metadata to SQLite database.')
    parser.add_argument('-f', '--fasta_file', help='Path to the FASTA file.', required=True)
    parser.add_argument('-m', '--metadata_file', help='Path to the metadata CSV file.', required=False)
    
    args = parser.parse_args()
    
    main(args.fasta_file, args.metadata_file)
