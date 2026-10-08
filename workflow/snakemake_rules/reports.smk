"""
Reports produced by the workflow. There are two, and they answer different
questions:

  1. Surveillance report  ->  reports/
     "What did we sequence?"  Type/subtype/clade frequencies and per-run QC
     for every specimen. Built by the `surveillance_report` rule below, which
     runs scripts/report.py.

  2. Run report  ->  .run/
     "How did this run go on this machine?"  Provenance (host, git commit,
     tool versions), job times, runtime and memory per rule. Built at the end
     of every run, successful or failed, by the onstart / onsuccess / onerror
     handlers below, which run scripts/run_report.py.

This file is included from the Snakefile after ingest.smk, because the
surveillance report reads jhh_metadata, jhh_sequences and flusort_metadata,
which ingest.smk defines.
"""


# ===========================================================================
# 1. Surveillance report
# ===========================================================================
#
# Outputs (all under reports/):
#   surveillance_report.html      interactive page; opens offline in any browser
#   surveillance_report.pptx      PowerPoint deck
#   report.tsv, report.xlsx       one row per specimen
#   figures/ (PNG), tables/ (TSV) for reuse in slides and papers
#
# Settings (title, notes, plot window):  config/report.yaml
# Skip it for one run:                   snakemake ... --config surveillance_report=false
# Rebuild it by hand:                    python scripts/report.py
# Explore it interactively:              marimo run scripts/report.py

REPORT_SUBTYPES = ["h3n2", "h1n1", "vic"]
REPORT_BUILDS = ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns",  # 8 segment builds
                 "genome"]                                          # + whole-genome build

SURVEILLANCE_REPORT_FILES = [
    "reports/surveillance_report.html",
    "reports/surveillance_report.pptx",
    "reports/report.tsv",
    "reports/report.xlsx",
]


def surveillance_report_wanted():
    """
    True unless the run was started with --config surveillance_report=false.
    Values given on the command line arrive as text, so "false", "0", "no"
    and "off" all switch the report off.
    """
    setting = str(config.get("surveillance_report", True)).strip().lower()
    return setting not in ("false", "0", "no", "off")


def surveillance_report_targets(wildcards):
    """
    The report files for `rule all` (and snapshot_clean_after_build) to
    request; an empty list when the report is switched off.
    """
    if surveillance_report_wanted():
        return SURVEILLANCE_REPORT_FILES
    return []


rule surveillance_report:
    message: "Building the surveillance report (HTML + PowerPoint)"
    input:
        # Finished Auspice trees, one per subtype x build
        auspice = expand("auspice/{subtype}/{build}.json",
                         subtype=REPORT_SUBTYPES, build=REPORT_BUILDS),
        # augur filter's record of which strains were removed and why
        # (written by augur_filter in segments.smk and genome_filter in genomes.smk)
        filter_logs = expand("results/{subtype}/{build}/filter_log.tsv",
                             subtype=REPORT_SUBTYPES, build=REPORT_BUILDS),
        # flusort's typing of every JHH specimen (from ingest.smk)
        flusort = flusort_metadata,
        report_config = "config/report.yaml",
        # listed so that editing the report script rebuilds the report
        script = "scripts/report.py"
    output:
        SURVEILLANCE_REPORT_FILES
    params:
        # the submitted JHH specimen metadata and sequences (paths set in ingest.smk)
        jhh_metadata = jhh_metadata,
        jhh_sequences = jhh_sequences
    log:
        ".run/logs/surveillance_report/surveillance_report.log"
    benchmark:
        ".run/benchmarks/surveillance_report/surveillance_report.tsv"
    shell:
        """
        exec > {log} 2>&1
        python -u scripts/report.py \
            --outdir reports \
            --config {input.report_config} \
            --jhh-metadata {params.jhh_metadata} \
            --jhh-sequences {params.jhh_sequences} \
            --flusort-metadata {input.flusort}
        """


# ===========================================================================
# 2. Run report (provenance, timing and memory for each Snakemake run)
# ===========================================================================
#
# Everything a run writes about itself lives under .run/:
#   .run/logs/{rule}/{subtype}_{segment}.log            each job's stdout + stderr
#   .run/benchmarks/{rule}/{subtype}_{segment}.tsv      each job's runtime and memory
#   .run/run_logs/{RUN_ID}_provenance.txt               host, git commit, tool versions,
#                                                       start/finish time, status
#   .run/run_logs/{RUN_ID}_snakemake_{SUCCESS|FAILED}.log   copy of Snakemake's main log
#   .run/reports/{RUN_ID}/report.md (+ figures/, tables/)   the run report itself
#
# snapshot_clean archives and clears .run/logs/ and .run/benchmarks/, but keeps
# .run/run_logs/ and .run/reports/ so run history builds up over time.
# This is separate from Snakemake's own `--report` output.
#
# Rebuild a run report by hand:
#   python scripts/run_report.py                     # latest run
#   python scripts/run_report.py --run-id <RUN_ID>   # a specific run
#   python scripts/run_report.py --all               # every run

RUN_ID = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")   # e.g. 20261006T191100
RUN_DIR = ".run"
RUN_LOG_DIR = f"{RUN_DIR}/run_logs"
PROVENANCE_FILE = f"{RUN_LOG_DIR}/{RUN_ID}_provenance.txt"

# A note on the shell() commands below: {NAME} is filled in from the Python
# variables above (RUN_ID, PROVENANCE_FILE, ...). A brace meant for the shell
# itself is written doubled, {{ }}. Paths are wrapped in "double quotes" so a
# repository folder with a space in its name (e.g. "local repositories") still
# works; without them the shell splits the path into two arguments.


# At the start of a run: record where, when and with what it is running.
onstart:
    shell(
        """
        mkdir -p "{RUN_LOG_DIR}"
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
            echo "iqtree:     $( (iqtree3 --version || iqtree2 --version || iqtree --version) 2>/dev/null | grep -m1 -i 'iq-tree' || echo 'not found')"
            echo "python:     $(python --version 2>&1)"
            echo "conda env:  ${{CONDA_DEFAULT_ENV:-none}} (${{CONDA_PREFIX:-no conda prefix}})"
        }} > "{PROVENANCE_FILE}" 2>&1

        # Data protection (never stops the run): warn if GISAID data sits
        # outside source/, or if this clone's commit/push checks are off.
        bash scripts/data_guard.sh --scan || true
        [ "$(git config --get core.hooksPath)" = ".githooks" ] \
            || echo "WARNING: data-protection git hooks are OFF. Turn them on: git config core.hooksPath .githooks"
        """
    )


def finish_run_report(status, snakemake_log):
    """
    Close out the run: stamp the finish time and status into the provenance
    file, keep a copy of Snakemake's main log, then build the run report.
    If the report itself fails, only a warning is printed; it never changes
    the run's exit status.
    """
    shell(
        """
        mkdir -p "{RUN_LOG_DIR}"
        echo "finished_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "{PROVENANCE_FILE}"
        echo "status:     {status}" >> "{PROVENANCE_FILE}"
        cp "{snakemake_log}" "{RUN_LOG_DIR}/{RUN_ID}_snakemake_{status}.log"
        python scripts/run_report.py --run-dir "{RUN_DIR}" --run-id {RUN_ID} \
            || echo "WARNING: run report failed; rerun with: python scripts/run_report.py --run-id {RUN_ID}"
        """
    )


# At the end of a run. `log` is the path to Snakemake's main log for this run.
onsuccess:
    finish_run_report("SUCCESS", log)

onerror:
    finish_run_report("FAILED", log)
