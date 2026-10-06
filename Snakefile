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
# Run outputs: everything a run writes about itself lives under .run/
#   - Per-job logs:        .run/logs/{rule}/{subtype}_{segment}.log  (stdout + stderr)
#   - Per-job benchmarks:  .run/benchmarks/{rule}/{subtype}_{segment}.tsv
#   - Per-run provenance:  .run/run_logs/{RUN_ID}_provenance.txt
#   - Per-run main log:    .run/run_logs/{RUN_ID}_snakemake_{SUCCESS|FAILED}.log
#   - Per-run reports:     .run/reports/{RUN_ID}/report.md (+ figures/, tables/)
# .run/run_logs/ and .run/reports/ are kept across snapshot_clean so run
# history persists; .run/logs/ and .run/benchmarks/ are archived and cleared.
# Run reports are separate from Snakemake's native --report output.
# ---------------------------------------------------------------------------
RUN_ID = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
RUN_DIR = ".run"
RUN_LOG_DIR = f"{RUN_DIR}/run_logs"

onstart:
    # shell() fills {RUN_ID}/{RUN_LOG_DIR} from the Snakefile's variables;
    # literal shell braces are escaped as {{ }}.
    shell(
        """
        mkdir -p {RUN_LOG_DIR}
        {{
            echo "run_id:     {RUN_ID}"
            echo "started:    $(date)"
            echo "started_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
            echo "host:       $(hostname)"
            echo "user:       $(id -un 2>/dev/null || echo "uid $(id -u)")"
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
            echo "iqtree:     $( (iqtree2 --version || iqtree --version) 2>/dev/null | grep -m1 -i 'iq-tree' || echo 'not found')"
            echo "python:     $(python --version 2>&1)"
        }} > {RUN_LOG_DIR}/{RUN_ID}_provenance.txt 2>&1
        """
    )

# On finish: stamp the end time into the provenance file, keep a copy of
# Snakemake's main log (`log`), then build the run report. A report failure
# only prints a warning; it never changes the run's exit status.
onsuccess:
    shell(
        """
        mkdir -p {RUN_LOG_DIR}
        echo "finished_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> {RUN_LOG_DIR}/{RUN_ID}_provenance.txt
        echo "status:     SUCCESS" >> {RUN_LOG_DIR}/{RUN_ID}_provenance.txt
        cp {log} {RUN_LOG_DIR}/{RUN_ID}_snakemake_SUCCESS.log
        python scripts/run_report.py --run-dir {RUN_DIR} --run-id {RUN_ID} \
            || echo "WARNING: run report failed; rerun with: python scripts/run_report.py --run-id {RUN_ID}"
        """
    )

onerror:
    shell(
        """
        mkdir -p {RUN_LOG_DIR}
        echo "finished_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> {RUN_LOG_DIR}/{RUN_ID}_provenance.txt
        echo "status:     FAILED" >> {RUN_LOG_DIR}/{RUN_ID}_provenance.txt
        cp {log} {RUN_LOG_DIR}/{RUN_ID}_snakemake_FAILED.log
        python scripts/run_report.py --run-dir {RUN_DIR} --run-id {RUN_ID} \
            || echo "WARNING: run report failed; rerun with: python scripts/run_report.py --run-id {RUN_ID}"
        """
    )

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
# No log: directive here because the script itself deletes .run/logs/.
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
