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
               subtype=["h3n2", "h1n1", "vic"])

include: "workflow/snakemake_rules/ingest.smk"
include: "workflow/snakemake_rules/segments.smk"
include: "workflow/snakemake_rules/genomes.smk"