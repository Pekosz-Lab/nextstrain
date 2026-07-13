import subprocess
import os

# Map of original subtype names to their desired lowercase equivalents
subtype_map = {
    "H1N1": "h1n1",
    "H3N2": "h3n2",
    "Victoria": "vic"
}

# Path to the SQLite database
db_path = "fludb.db"

# Loop through each subtype and execute the command
for subtype, dir_name in subtype_map.items():
    # Define the output file paths
    fasta_file = f"data/{dir_name}/genome/sequences.fasta"
    metadata_file = f"data/{dir_name}/genome/metadata.tsv"

    # Create the output directories if they don't exist
    os.makedirs(os.path.dirname(fasta_file), exist_ok=True)

    # Build the command
    command = [
        "python", "fludb/scripts/download_concatenated.py",
        "-d", db_path,
        "-f", fasta_file,
        "-m", metadata_file,
        "--headers", "sequence_ID",
        "--filters", f"subtype='{subtype}'",
        "--complete-genomes",
        "--concatenate"
    ]

    # Execute the command
    try:
        subprocess.run(command, check=True)
        print(f"Downloaded data for {subtype} into {fasta_file} and {metadata_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading data for {subtype}: {e}")