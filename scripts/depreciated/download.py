import argparse
import sqlite3
import pandas as pd

# Function to fetch data from the database with optional filters and segment selection
def fetch_data_from_db(db_path, filters, segments, complete_genomes):
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        raise ConnectionError(f"Failed to connect to database: {e}")

    # Construct the SQL query
    query = """
    SELECT sequence_ID, sample_ID, type, subtype, date, passage_history, study_id,
           sequencing_run, location, database_origin
    """
    # Include the required segments in the query
    if segments:
        query += ", " + ", ".join(segments)
    else:
        query += ", pb2, pb1, pa, ha, np, na, mp, ns"

    query += " FROM influenza_genomes WHERE 1=1"

    # Apply filters if provided
    if filters:
        query += " AND " + " AND ".join(filters)

    # Apply complete genomes filter if requested
    if complete_genomes:
        query += """
        AND pb2 IS NOT NULL AND pb1 IS NOT NULL AND pa IS NOT NULL AND 
            ha IS NOT NULL AND np IS NOT NULL AND na IS NOT NULL AND 
            mp IS NOT NULL AND ns IS NOT NULL
        """

    try:
        df = pd.read_sql_query(query, conn)
    except pd.io.sql.DatabaseError as e:
        conn.close()
        raise RuntimeError(f"Error executing query: {e}")

    conn.close()

    # Clean the date field for consistent formatting
    df['date'] = df['date'].apply(clean_date_format)

    return df


# Function to clean and standardize the date format
def clean_date_format(date):
    if pd.isna(date):
        return 'XXXX-XX-XX'  # Placeholder for missing dates
    parts = date.split('-')
    if len(parts) == 1:
        return f"{parts[0]}-XX-XX"  # Year only
    elif len(parts) == 2:
        return f"{parts[0]}-{parts[1]}-XX"  # Year and month only
    return date  # Already in YYYY-MM-DD format

# Function to generate the FASTA file
def generate_fasta(df, fasta_file, headers, segments, header_delimiter):
    fasta_seq_ids = set()

    # Ensure headers include sequence_ID or sample_ID
    if not any(field in headers for field in ['sequence_ID', 'sample_ID']):
        raise ValueError("At least 'sequence_ID' or 'sample_ID' must be included in headers.")

    with open(fasta_file, 'w') as f:
        for _, row in df.iterrows():
            sequence_id = row['sequence_ID']
            # Fetch sequence data for each specified segment
            segments_dict = {segment: row[segment] for segment in segments if pd.notna(row[segment])}
            if segments_dict:
                for segment_name, sequence in segments_dict.items():
                    # Build the FASTA header based on specified fields
                    header_parts = []
                    if 'sequence_ID' in headers:
                        header_parts.append(row.get('sequence_ID', 'NA'))
                    if 'sample_ID' in headers:
                        header_parts.append(row.get('sample_ID', 'NA'))
                    if 'type' in headers:
                        header_parts.append(row.get('type', 'NA'))
                    if 'subtype' in headers:
                        header_parts.append(row.get('subtype', 'NA'))
                    if 'date' in headers:
                        header_parts.append(row.get('date', 'NA'))
                    if 'passage_history' in headers:
                        header_parts.append(row.get('passage_history', 'NA'))
                    if 'study_id' in headers:
                        header_parts.append(row.get('study_id', 'NA'))
                    if 'location' in headers:
                        header_parts.append(row.get('location', 'NA'))
                    if 'database_origin' in headers:
                        header_parts.append(row.get('database_origin', 'NA'))
                    if 'segment' in headers:
                        header_parts.append(segment_name)
                    if 'sequencing_run' in headers:
                        header_parts.append(row.get('sequencing_run', 'NA'))

                    # Create the final header string
                    header = header_delimiter.join(header_parts)
                    f.write(f">{header}\n{sequence}\n")
                
                # Track sequence_IDs for metadata file filtering
                fasta_seq_ids.add(sequence_id)

    return fasta_seq_ids

# Function to generate the metadata file
def generate_metadata(df, metadata_file, fasta_seq_ids):
    # Drop sequence columns
    metadata_df = df.drop(columns=['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns'], errors='ignore')

    # Filter metadata to include only entries present in the FASTA file
    metadata_df = metadata_df[metadata_df['sequence_ID'].isin(fasta_seq_ids)]
    metadata_df.to_csv(metadata_file, sep='\t', index=False)

# Main function to handle argument parsing and workflow execution
def main(db_path, fasta_file, metadata_file, headers, filters, segments, complete_genomes, header_delimiter):
    df = fetch_data_from_db(db_path, filters, segments, complete_genomes)
    fasta_seq_ids = generate_fasta(df, fasta_file, headers, segments, header_delimiter)
    generate_metadata(df, metadata_file, fasta_seq_ids)

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Output FASTA and metadata files from a SQLite database with query filters.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the output FASTA file.')
    parser.add_argument('-m', '--metadata', required=True, help='Path to the output metadata TSV file.')
    parser.add_argument('--headers', nargs='*', choices=['sequence_ID', 'sample_ID', 'type', 'subtype', 'date', 'passage_history', 'study_id', 'location', 'database_origin', 'segment', 'sequencing_run'], default=['sequence_ID'], help='Metadata fields to include in the FASTA header.')
    parser.add_argument('--filters', nargs='*', help='SQL conditions for querying the database. Example: "type=\'InfluenzaB\'", "date BETWEEN \'2024-01-01\' AND \'2024-12-31\'".')
    parser.add_argument('--segments', nargs='*', choices=['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns'], help='Specific segments to include in the FASTA file.')
    parser.add_argument('--complete-genomes', action='store_true', help='Filter for complete genomes (samples with all 8 segments).')
    parser.add_argument('--header-delimiter', default='|', help='Delimiter to use between fields in the FASTA header. Default is "|".')

    args = parser.parse_args()

    # Parse filters
    filters = args.filters if args.filters else []

    # Parse segments
    segments = args.segments if args.segments else ['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns']

    main(args.db, args.fasta, args.metadata, args.headers, filters, segments, args.complete_genomes, args.header_delimiter)
