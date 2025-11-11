import sqlite3

# Connect to the database (or create it if it doesn't exist)
conn = sqlite3.connect('fludb.db')
cursor = conn.cursor()

# Create the table with additional columns for location and database origin
cursor.execute('''
CREATE TABLE IF NOT EXISTS influenza_genomes (
    sequence_ID TEXT PRIMARY KEY,
    sample_ID TEXT,
    type TEXT,
    subtype TEXT,
    date TEXT,
    passage_history TEXT,
    study_id TEXT,
    sequencing_run TEXT,
    location TEXT,
    database_origin TEXT, 
    age TEXT,
    age_unit TEXT,
    sex TEXT,
    pb2 TEXT,
    pb1 TEXT,
    pa TEXT,
    ha TEXT,
    np TEXT,
    na TEXT,
    mp TEXT,
    ns TEXT
)
''')

# Commit the changes and close the connection
conn.commit()
conn.close()