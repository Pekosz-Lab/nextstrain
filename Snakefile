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
        lambda wildcards: "snapshots/snapshot_clean.done" if config.get("snapshot_clean", False) else []

include: "workflow/snakemake_rules/ingest.smk"
include: "workflow/snakemake_rules/segments.smk"
include: "workflow/snakemake_rules/genomes.smk"



# Manual snapshot-and-clean target. With no output marker, explicitly invoking
# this rule runs it every time, even when snapshot_clean.done already exists.
rule snapshot_clean:
    """
    Create a timestamped snapshot and clean the workspace immediately.
    """
    shell:
        "bash scripts/snapshot_clean.sh"


# Configuration-driven snapshot target. The completion marker lets rule all
# depend on cleanup, while the build outputs ensure cleanup runs last and is
# retriggered after a subsequent build recreates those outputs.
rule snapshot_clean_after_build:
    input:
        expand(
            "auspice/{subtype}/{segment}_tip-frequencies.json",
            subtype=["h3n2", "h1n1", "vic"],
            segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"],
        ),
        expand(
            "auspice/{subtype}/{segment}.json",
            subtype=["h3n2", "h1n1", "vic"],
            segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"],
        ),
        expand(
            "auspice/{subtype}/genome_tip-frequencies.json",
            subtype=["h3n2", "h1n1", "vic"],
        ),
        expand(
            "auspice/{subtype}/genome.json",
            subtype=["h3n2", "h1n1", "vic"],
        )
    output:
        touch("snapshots/snapshot_clean.done")
    shell:
        "bash scripts/snapshot_clean.sh"
