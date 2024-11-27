import argparse
import sqlite3
import pandas as pd

def fetch_data_from_db(db_path, filters, segments):
    conn = sqlite3.connect(db_path)
    query = "SELECT seq_id, sample_id, subtype, collection_date, passage_history, study_id, sequencing_run"
    
    # Add segment columns dynamically based on the segments filter
    if segments:
        query += ", " + ", ".join(segments)
    else:
        query += ", pb2, pb1, pa, ha, np, na, mp, ns"
    
    query += " FROM influenza_genomes WHERE 1=1"
    
    # Incorporate SQL filters
    if filters:
        query += " AND " + " AND ".join(filters)
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Clean the collection_date format
    df['collection_date'] = df['collection_date'].apply(clean_collection_date)
    
    return df

def clean_collection_date(date):
    if pd.isna(date):
        return 'XX-XX-XX'  # Placeholder for missing dates
    parts = date.split('-')
    if len(parts) == 1:  # Only year
        return f"{parts[0]}-XX-XX"
    elif len(parts) == 2:  # Year and month
        return f"{parts[0]}-{parts[1]}-XX"
    return date  # Already in YYYY-MM-DD format

def generate_fasta(df, fasta_file, headers, segments):
    fasta_seq_ids = set()
    
    # Ensure that seq_id or sample_id is included in headers
    if not any(field in headers for field in ['seq_id', 'sample_id']):
        raise ValueError("At least 'seq_id' or 'sample_id' must be included in headers.")
    
    with open(fasta_file, 'w') as f:
        for _, row in df.iterrows():
            seqid = row['seq_id']
            # Fetch sequence data for each specified segment
            segments_dict = {segment: row[segment] for segment in segments if pd.notna(row[segment])}
            if segments_dict:
                for segment_name, sequence in segments_dict.items():
                    # Build the FASTA header based on specified fields
                    header_parts = []
                    if 'seq_id' in headers:
                        header_parts.append(row.get('seq_id', 'NA'))
                    if 'sample_id' in headers:
                        header_parts.append(row.get('sample_id', 'NA'))
                    if 'subtype' in headers:
                        header_parts.append(row.get('subtype', 'NA'))
                    if 'collection_date' in headers:
                        header_parts.append(row.get('collection_date', 'NA'))
                    if 'passage_history' in headers:
                        header_parts.append(row.get('passage_history', 'NA'))
                    if 'study_id' in headers:
                        header_parts.append(row.get('study_id', 'NA'))
                    if 'segment' in headers:
                        header_parts.append(segment_name)
                    if 'sequencing_run' in headers:
                        header_parts.append(row.get('sequencing_run', 'NA'))

                    # Create the final header string
                    header = "|".join(header_parts)
                    f.write(f">{header}\n{sequence}\n")
                
                # Track seq_ids for metadata file filtering
                fasta_seq_ids.add(seqid)

    return fasta_seq_ids

def generate_metadata(df, metadata_file, fasta_seq_ids):
    # Drop sequence columns
    metadata_df = df.drop(columns=['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns'], errors='ignore')
    
    # Filter metadata to include only entries present in the FASTA file
    metadata_df = metadata_df[metadata_df['seq_id'].isin(fasta_seq_ids)]
    metadata_df.to_csv(metadata_file, sep='\t', index=False)

def main(db_path, fasta_file, metadata_file, headers, filters, segments):
    df = fetch_data_from_db(db_path, filters, segments)
    fasta_seq_ids = generate_fasta(df, fasta_file, headers, segments)
    generate_metadata(df, metadata_file, fasta_seq_ids)

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Output FASTA and metadata files from a SQLite database with query filters.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the output FASTA file.')
    parser.add_argument('-m', '--metadata', required=True, help='Path to the output metadata TSV file.')
    parser.add_argument('--headers', nargs='*', choices=['seq_id', 'sample_id', 'subtype', 'collection_date', 'passage_history', 'study_id', 'segment', 'sequencing_run'], default=['seq_id'], help='Metadata fields to include in the FASTA header.')
    parser.add_argument('--filters', nargs='*', help='SQL conditions for querying the database are accepted. Use AND, OR, and NOT for complex queries. \n Passage History Example: "passage_history=\'hNEC1S2\'" \n Date range example: "collection_date BETWEEN \'2024-01-01\' AND \'2024-12-31\'"')
    parser.add_argument('--segments', nargs='*', choices=['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns'], help='Specific segments to include in the FASTA file. Example: ha pb1')

    args = parser.parse_args()

    # Parse filters
    filters = args.filters if args.filters else []

    # Parse segments
    segments = args.segments if args.segments else ['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns']

    main(args.db, args.fasta, args.metadata, args.headers, filters, segments)