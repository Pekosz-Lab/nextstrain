import os
import datetime
import pandas as pd
from treetime.utils import numeric_date

wildcard_constraints:
    subtype = "h1n1|h3n2|vic",
    segment = "pb2|pb1|pa|ha|np|na|mp|ns"

# Define the mimimum length thresholds for each segment. This is a crude filtering which should be fine-tuned in the future depending on build results. 
min_lengths = {
    "pb2": 2000,
    "pb1": 2000,
    "pa": 1800,
    "ha": 1400,
    "np": 1200,
    "na": 1200,
    "mp": 700,
    "ns": 700
}

rule all:
    input:
        # Individual segments
        expand("auspice/{subtype}/{segment}_tip-frequencies.json", 
               subtype=["h3n2", "h1n1", "vic"], 
               segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("auspice/{subtype}/{segment}.json", 
               subtype=["h3n2", "h1n1", "vic"], 
               segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),

        # Genomes
        expand("auspice/{subtype}/genome_tip-frequencies.json", 
               subtype=["h3n2", "h1n1", "vic"]),
        expand("auspice/{subtype}/genome.json", 
               subtype=["h3n2", "h1n1", "vic"]),
        lambda wildcards: "logs/snapshot_clean.done" if config.get("snapshot_clean", False) else []

include: "workflow/snakemake_rules/ingest.smk"
include: "workflow/snakemake_rules/segments.smk"
include: "workflow/snakemake_rules/genomes.smk"



# snapshot and clean feature 
rule snapshot_clean:
    """
    Optionally triggered snapshot-and-clean step.
    Creates a timestamped local snapshot of outputs and cleans the workspace.
    Also removes flusort-related files from the source directory.
    """
    output:
        touch("logs/snapshot_clean.done")
    shell:
        """
        # Create snapshots directory if it does not exist
        mkdir -p snapshots

        # Generate local timestamp (ISO-like format using local time)
        TIMESTAMP=$(date +"%Y%m%dT%H%M%S")

        SNAPSHOT_DIR="snapshots/${{TIMESTAMP}}"
        mkdir -p "$SNAPSHOT_DIR"

        echo "📸 Creating snapshot in $SNAPSHOT_DIR"

        # Copy key folders if they exist
        for folder in auspice logs reports source nextclade; do
            if [ -d "$folder" ]; then
                echo "→ Copying $folder/"
                cp -r "$folder" "$SNAPSHOT_DIR/"
            fi
        done

        echo "🗜️ Compressing snapshot..."
        tar -czf "snapshots/${{TIMESTAMP}}.tar.gz" -C "snapshots" "${{TIMESTAMP}}"

        # Optionally remove the uncompressed snapshot folder after compression
        rm -rf "$SNAPSHOT_DIR"

        echo "🧹 Cleaning up workspace..."

        # Remove working directories
        rm -rf data results logs reports auspice

        # Remove the database if it exists
        if [ -f fludb.db ]; then
            rm -f fludb.db
        fi

        # Remove specific flusort-related files but keep the source directory
        if [ -d source ]; then
            echo "🗑️  Removing flusort files from source/"
            rm -f source/flusort_*
        fi

        echo "✅ Snapshot created at snapshots/${{TIMESTAMP}}.tar.gz"
        echo "✅ Cleanup complete."
        """