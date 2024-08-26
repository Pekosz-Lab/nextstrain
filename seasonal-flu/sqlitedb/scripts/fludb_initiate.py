import sqlite3

conn = sqlite3.connect('fludb.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS influenza_genomes (
    seq_id TEXT PRIMARY KEY,
    sample_id TEXT,
    subtype TEXT,
    collection_date TEXT,
    passage_history TEXT,
    study_id TEXT,
    sequencing_run TEXT,
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

# Save (commit) the changes
conn.commit()

# Close the connection
conn.close()
