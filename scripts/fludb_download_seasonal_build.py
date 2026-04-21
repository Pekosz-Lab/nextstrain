import os
import subprocess
from collections import defaultdict

# Define the parameters
db_path = "fludb.db"
fasta_dir = "data"
metadata_dir = "data"
headers = ["sample_ID"]
header_delimiter = "_"  # Added header delimiter
raw_subtypes = ["H1N1", "H1xx", "xxN1", "H3N2", "H3xx", "xxN2", "Victoria"]  # Includes raw subtype patterns from flusort output. 
segments = ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]

# Normalize raw subtypes to standardized values
def normalize_subtype(subtype):
    """Normalize raw subtypes to standardized values for filtering."""
    if subtype in ("H1N1", "H1xx", "xxN1"):
        return "H1N1"  # Used in --filters flag
    elif subtype in ("H3N2", "H3xx", "xxN2"):
        return "H3N2"  # Used in --filters flag
    elif "Victoria" in subtype:
        return "Victoria"  # Used in --filters flag
    else:
        raise ValueError(f"Unknown subtype pattern: {subtype}")

# Group raw subtype patterns by their normalized (complete) subtype value.
# This ensures that partial patterns stored in the database (e.g. 'H1xx', 'xxN1')
# are all matched when filtering, rather than only exact matches on 'H1N1'.
subtype_groups = defaultdict(list)
for raw in raw_subtypes:
    subtype_groups[normalize_subtype(raw)].append(raw)

# Loop through each normalized subtype and segment
for subtype, raw_patterns in subtype_groups.items():
    # Handle directory name explicitly for 'Victoria' as 'vic'
    if subtype == "Victoria":
        dir_subtype = "vic"
    else:
        dir_subtype = subtype.lower()

    # Build SQL IN clause to match all partial and complete patterns for this subtype
    in_values = ", ".join(f"'{p}'" for p in raw_patterns)

    for segment in segments:
        # Define the directory structure using lowercase values for directories
        output_dir = f"{fasta_dir}/{dir_subtype}/{segment}"
        
        # Ensure the directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Construct the output file names
        fasta_file = f"{output_dir}/sequences.fasta"
        metadata_file = f"{output_dir}/metadata.tsv"
        
        # Construct the command; use IN clause to match all subtype patterns for this group
        cmd = [
            "python", "fludb/scripts/download.py",
            "--db", db_path,
            "--fasta", fasta_file,
            "--metadata", metadata_file,
            "--headers", *headers,
            "--header-delimiter", header_delimiter,
            "--filters", f"subtype IN ({in_values})",
            "--segments", segment
        ]

        # Print a concise message for logging purposes
        print(f"Downloading data for {subtype} - {segment} segment...")
        
        # Execute the command
        try:
            subprocess.run(cmd, check=True)
            print(f"Data downloaded successfully for {subtype} - {segment} segment.")
        except subprocess.CalledProcessError as e:
            print(f"Error while downloading data for {subtype} - {segment} segment.")
            print()