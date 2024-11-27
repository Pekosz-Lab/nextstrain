"""
This script downloads complete genomes for all subtypes and organizes them by subtype and segment. 
"""

import os
import subprocess

# Define the parameters
db_path = "fludb.db"
fasta_dir = "data"
metadata_dir = "data"
headers = "sequence_ID"
subtypes = ["H1N1", "H3N2", "Victoria"]
segments = ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]

# Loop through each subtype and segment
for subtype in subtypes:
    for segment in segments:
        # Define the directory structure
        output_dir = f"{fasta_dir}/{subtype}/{segment}"
        
        # Ensure the directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Construct the output file names
        fasta_file = f"{output_dir}/sequences.fasta"
        metadata_file = f"{output_dir}/metadata.tsv"
        
        # Construct the command
        cmd = [
            "python", "fludb/scripts/download.py",
            "--db", db_path,
            "--fasta", fasta_file,
            "--metadata", metadata_file,
            "--headers", headers,
            "--filters", f"subtype='{subtype}'",
            "--segments", segment,
            "--complete-genomes"  # Add the flag for complete genomes
        ]

        # Print a concise message for logging purposes
        print(f"Downloading data for {subtype} - {segment} segment with complete genomes...")
        
        # Execute the command
        try:
            subprocess.run(cmd, check=True)
            print(f"Data downloaded successfully for {subtype} - {segment} segment.")
        except subprocess.CalledProcessError as e:
            print(f"Error while downloading data for {subtype} - {segment} segment.")
            print(e)

# Function to rename directories
def rename_directories(base_dir, subtype_map):
    for subtype, renamed_subtype in subtype_map.items():
        old_dir = os.path.join(base_dir, subtype)
        new_dir = os.path.join(base_dir, renamed_subtype)
        if os.path.exists(old_dir):
            print(f"Renaming {old_dir} to {new_dir}")
            os.rename(old_dir, new_dir)
        else:
            print(f"Directory {old_dir} does not exist, skipping.")

# Map of original subtype names to their desired lowercase equivalents
subtype_map = {
    "H1N1": "h1n1",
    "H3N2": "h3n2",
    "Victoria": "vic"
}

# Rename the directories after processing
rename_directories(fasta_dir, subtype_map)
