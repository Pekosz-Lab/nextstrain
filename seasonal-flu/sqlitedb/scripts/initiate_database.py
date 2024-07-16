import sqlite3

# Connect to the database (creates it if it doesn't exist)
conn = sqlite3.connect('flu.db')

# Create a cursor object
cursor = conn.cursor()

# Create the sequences table
cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS sequences (
        sequence_id TEXT PRIMARY KEY,
        pb2 TEXT,
        pb1 TEXT,
        pa TEXT,
        ha TEXT,
        np TEXT,
        na TEXT,
        mp TEXT,
        ns TEXT
    )
    '''
)

# Create the metadata_flusort table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata_flusort (
        sequence_id TEXT PRIMARY KEY,
        type TEXT,
        ha_subtype TEXT,
        na_subtype TEXT,
        genome_completeness TEXT,
        FOREIGN KEY (sequence_id) REFERENCES sequences (sequence_id)
    )
    '''
)

# Create metadata_mostafa table
cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS metadata_mostafa (
        sequence_id TEXT PRIMARY KEY,
        deidentified_id TEXT,
        run_id TEXT,
        date_sequenced TEXT
    )
    '''
)

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database and tables created successfully.")
