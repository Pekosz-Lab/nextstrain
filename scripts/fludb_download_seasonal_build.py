import os
import subprocess

# Define the parameters
db_path = "fludb.db"
fasta_dir = "data"
metadata_dir = "data"
headers = ["sample_ID"]
header_delimiter = "_"  # Added header delimiter
raw_subtypes = ["H1xx", "xxN1", "H3xx", "xxN2", "Victoria"]  # Includes raw subtype patterns from flusort output. 
segments = ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]

# Normalize raw subtypes to standardized values
def normalize_subtype(subtype):
    """Normalize raw subtypes to standardized values for filtering."""
    if "H1" in subtype or "N1" in subtype:
        return "H1N1"  # Used in --filters flag
    elif "H3" in subtype or "N2" in subtype:
        return "H3N2"  # Used in --filters flag
    elif "Victoria" in subtype:
        return "Victoria"  # Used in --filters flag
    else:
        raise ValueError(f"Unknown subtype pattern: {subtype}")

# Normalize subtypes list for filtering
subtypes = [normalize_subtype(subtype) for subtype in raw_subtypes]

# Loop through each subtype and segment
for subtype in set(subtypes):  # Use `set` to avoid redundant processing
    # Handle directory name explicitly for 'Victoria' as 'vic'
    if subtype == "Victoria":
        dir_subtype = "vic"
    else:
        dir_subtype = subtype.lower()

    for segment in segments:
        # Define the directory structure using lowercase values for directories
        output_dir = f"{fasta_dir}/{dir_subtype}/{segment}"
        
        # Ensure the directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Construct the output file names
        fasta_file = f"{output_dir}/sequences.fasta"
        metadata_file = f"{output_dir}/metadata.tsv"
        
        # Construct the command with uppercase subtype for filtering
        cmd = [
            "python", "fludb/scripts/download.py",
            "--db", db_path,
            "--fasta", fasta_file,
            "--metadata", metadata_file,
            "--headers", *headers,
            "--header-delimiter", header_delimiter,
            "--filters", f"subtype='{subtype}'",  # Use the uppercase value for filters
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