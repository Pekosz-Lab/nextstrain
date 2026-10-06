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
# Logging conventions
#   - Per-job logs:        logs/{rule}/{subtype}_{segment}.log  (stdout + stderr)
#   - Per-job benchmarks:  benchmarks/{rule}/{subtype}_{segment}.tsv
#   - Per-run provenance:  run_logs/{RUN_ID}_provenance.txt
#   - Per-run main log:    run_logs/{RUN_ID}_snakemake_{SUCCESS|FAILED}.log
# run_logs/ is kept across snapshot_clean so run history persists, and is
# also copied into every snapshot archive.
# ---------------------------------------------------------------------------
RUN_ID = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
RUN_LOG_DIR = "run_logs"

onstart:
    # shell() fills {RUN_ID}/{RUN_LOG_DIR} from the Snakefile's variables;
    # literal shell braces are escaped as {{ }}.
    shell(
        """
        mkdir -p {RUN_LOG_DIR}
        {{
            echo "run_id:     {RUN_ID}"
            echo "started:    $(date)"
            echo "host:       $(hostname)"
            echo "user:       $(whoami)"
            echo "workdir:    $(pwd)"
            echo
            echo "== git =="
            git rev-parse HEAD 2>/dev/null || echo "not a git repository"
            git status --short 2>/dev/null || true
            echo
            echo "== tool versions =="
            echo "snakemake:  $(snakemake --version 2>&1 || echo 'not found')"
            echo "augur:      $(augur --version 2>&1 || echo 'not found')"
            echo "nextclade:  $(nextclade --version 2>&1 || echo 'not found')"
            echo "mafft:      $(mafft --version 2>&1 | head -n 1 || echo 'not found')"
            echo "iqtree:     $(iqtree2 --version 2>&1 | head -n 1 || echo 'not found')"
            echo "python:     $(python --version 2>&1)"
        }} > {RUN_LOG_DIR}/{RUN_ID}_provenance.txt 2>&1
        """
    )

onsuccess:
    # `log` is the path to Snakemake's own main log for this run
    shell("mkdir -p {RUN_LOG_DIR} && cp {log} {RUN_LOG_DIR}/{RUN_ID}_snakemake_SUCCESS.log")

onerror:
    shell("mkdir -p {RUN_LOG_DIR} && cp {log} {RUN_LOG_DIR}/{RUN_ID}_snakemake_FAILED.log")

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
# No log: directive here because the script itself deletes logs/.
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
