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

# ---------------------------------------------------------------------------
# Rules live in workflow/snakemake_rules/:
#   ingest.smk    type (flusort) and sort input sequences -> data/{subtype}/{segment|genome}/
#   segments.smk  one Nextstrain build per segment  -> auspice/{subtype}/{segment}.json
#   genomes.smk   whole-genome Nextstrain build     -> auspice/{subtype}/genome.json
#   reports.smk   the surveillance report (reports/) and the per-run report (.run/)
#   snapshot.smk  archive outputs to snapshots/ and clean the workspace
# ---------------------------------------------------------------------------
include: "workflow/snakemake_rules/ingest.smk"
include: "workflow/snakemake_rules/segments.smk"
include: "workflow/snakemake_rules/genomes.smk"
include: "workflow/snakemake_rules/reports.smk"   # must come after ingest.smk
include: "workflow/snakemake_rules/snapshot.smk"  # must come after reports.smk


rule all:
    # `snakemake` with no target runs this rule. (It is marked explicitly
    # because the included files above define their rules first.)
    default_target: True
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

        # Surveillance report (reports.smk); skip with --config surveillance_report=false
        surveillance_report_targets,

        # Snapshot and clean the workspace afterwards (snapshot.smk), if --config snapshot_clean=true
        snapshot_clean_targets
