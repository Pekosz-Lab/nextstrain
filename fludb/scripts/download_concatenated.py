import argparse
import sqlite3
import pandas as pd

# Function to fetch data from the database with optional filters and segment selection
def fetch_data_from_db(db_path, filters, segments, complete_genomes, concatenate):
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        raise ConnectionError(f"Failed to connect to database: {e}")

    # Construct the SQL query
    base_query = """
    SELECT sequence_ID, sample_ID, type, subtype, date, passage_history, study_id,
           sequencing_run, location, database_origin, age, age_unit, sex
    """

    if segments:
        base_query += ", " + ", ".join(segments)
    else:
        base_query += ", pb2, pb1, pa, ha, np, na, mp, ns"
    
    base_query += " FROM influenza_genomes WHERE 1=1"

    # Apply filters if provided
    if filters:
        base_query += " AND " + " AND ".join(filters)

    # Apply complete genomes filter if requested
    if complete_genomes:
        base_query += """
        AND pb2 IS NOT NULL AND pb1 IS NOT NULL AND pa IS NOT NULL AND 
            ha IS NOT NULL AND np IS NOT NULL AND na IS NOT NULL AND 
            mp IS NOT NULL AND ns IS NOT NULL
        """

    try:
        df = pd.read_sql_query(base_query, conn)
    except pd.io.sql.DatabaseError as e:
        conn.close()
        raise RuntimeError(f"Error executing query: {e}")

    conn.close()

    # Clean the date field for consistent formatting
    df['date'] = df['date'].apply(clean_date_format)

    # Concatenate segments if requested
    if concatenate and segments:
        df["concatenated_sequence"] = df[segments].apply(lambda row: "".join(row.dropna().astype(str)), axis=1)

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
def generate_fasta(df, fasta_file, headers, segments, header_delimiter, concatenate):
    fasta_seq_ids = set()
    with open(fasta_file, 'w') as f:
        for _, row in df.iterrows():
            sequence_id = row['sequence_ID']
            
            # Build the FASTA header
            header_parts = [str(row.get(field, '')) for field in headers if field in row]
            header = header_delimiter.join(header_parts)
            
            # Determine sequence to write
            if concatenate:
                sequence = row.get("concatenated_sequence", "")
            else:
                sequence = "".join([row[seg] for seg in segments if pd.notna(row[seg])])
            
            if sequence:
                f.write(f">{header}\n{sequence}\n")
                fasta_seq_ids.add(sequence_id)
    return fasta_seq_ids

# Function to generate the metadata file
def generate_metadata(df, metadata_file, fasta_seq_ids):
    metadata_df = df.drop(columns=['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns', 'concatenated_sequence'], errors='ignore')
    metadata_df = metadata_df[metadata_df['sequence_ID'].isin(fasta_seq_ids)]
    metadata_df.to_csv(metadata_file, sep='\t', index=False)

# Main function to handle argument parsing and workflow execution
def main(db_path, fasta_file, metadata_file, headers, filters, segments, complete_genomes, header_delimiter, concatenate):
    df = fetch_data_from_db(db_path, filters, segments, complete_genomes, concatenate)
    fasta_seq_ids = generate_fasta(df, fasta_file, headers, segments, header_delimiter, concatenate)
    generate_metadata(df, metadata_file, fasta_seq_ids)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Output FASTA and metadata files from a SQLite database with query filters.")
    parser.add_argument('-d', '--db', required=True, help='Path to the SQLite database file.')
    parser.add_argument('-f', '--fasta', required=True, help='Path to the output FASTA file.')
    parser.add_argument('-m', '--metadata', required=True, help='Path to the output metadata TSV file.')
    parser.add_argument('--headers', nargs='*', choices=['sequence_ID', 'sample_ID', 'type', 'subtype', 'date', 'passage_history', 'study_id', 'location', 'database_origin', 'segment', 'sequencing_run', 'age', 'age_unit', 'sex'], default=['sequence_ID'], help='Metadata fields to include in the FASTA header.')
    parser.add_argument('--filters', nargs='*', help='SQL conditions for querying the database. Example: "type=\'InfluenzaB\'", "date BETWEEN \'2024-01-01\' AND \'2024-12-31\'".')
    parser.add_argument('--segments', nargs='*', choices=['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns'], help='Specific segments to include in the FASTA file.') # not used here 
    parser.add_argument('--complete-genomes', action='store_true', help='Filter for complete genomes (samples with all 8 segments).')
    parser.add_argument('--header-delimiter', default='|', help='Delimiter to use between fields in the FASTA header. Default is "|".')
    parser.add_argument('--concatenate', action='store_true', help='Concatenate selected segments into a single sequence.')

    args = parser.parse_args()
    filters = args.filters if args.filters else []
    segments = args.segments if args.segments else ['pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns']
    
    main(args.db, args.fasta, args.metadata, args.headers, filters, segments, args.complete_genomes, args.header_delimiter, args.concatenate)
