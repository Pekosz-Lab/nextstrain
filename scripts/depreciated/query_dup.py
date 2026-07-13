import sqlite3
import pandas as pd

def find_duplicate_sample_ids(db_path, study_id):
    conn = sqlite3.connect(db_path)
    
    # SQL query to find duplicate sample_ids with unique seq_ids in a specific study group
    query = f"""
    SELECT sample_id, COUNT(seq_id) as seq_count
    FROM influenza_genomes
    WHERE study_id = '{study_id}'
    GROUP BY sample_id
    HAVING seq_count > 1;
    """
    
    # Execute the query and store the result in a pandas DataFrame
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

# Example usage:
db_path = 'fludb.db'
study_id = 'CEIRR_Macha_2021'
duplicates_df = find_duplicate_sample_ids(db_path, study_id)

# Print the result
print(duplicates_df)