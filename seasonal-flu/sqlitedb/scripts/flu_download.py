import sqlite3
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO

def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file."""
    conn = sqlite3.connect(db_file)
    return conn

def download_sequences(conn, output_fasta):
    """Download sequences from the database and write them to a FASTA file."""
    cursor = conn.cursor()

    # Query sequences and metadata
    cursor.execute('''
    SELECT sequences.sequence_id, sequences.pb2, sequences.pb1, sequences.pa, sequences.ha, sequences.np, sequences.na, sequences.mp, sequences.ns,
           metadata.type, metadata.ha_subtype, metadata.na_subtype, metadata.genome_completeness, metadata.date_sequenced
    FROM sequences
    LEFT JOIN metadata ON sequences.sequence_id = metadata.sequence_id
    ''')

    # Fetch all results
    rows = cursor.fetchall()

    # Write sequences to FASTA file
    with open(output_fasta, 'w') as fasta_file:
        for row in rows:
            sequence_id = row[0]
            segments = row[1:9]
            metadata = row[9:]

            for i, segment in enumerate(['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns']):
                if segments[i]:
                    header = f"{sequence_id}_{segment.upper()}"
                    sequence = Seq(segments[i])
                    record = SeqRecord(sequence, id=header, description="")
                    SeqIO.write(record, fasta_file, "fasta")

def main(db_file, output_fasta):
    # Create a database connection
    conn = create_connection(db_file)

    # Download sequences
    download_sequences(conn, output_fasta)

    # Close the database connection
    conn.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python download_data.py <db_file> <output_fasta>")
    else:
        db_file = sys.argv[1]
        output_fasta = sys.argv[2]
        main(db_file, output_fasta)
