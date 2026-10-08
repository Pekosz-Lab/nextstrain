"""
Snapshot and clean the workspace.

Both rules run scripts/snapshot_clean.sh, which:
  1. archives auspice/, .run/, reports/, source/, nextclade/, results/ and
     config/ into snapshots/{YYYYMMDDTHHMMSS}.tar.gz, then
  2. deletes data/, results/, reports/, auspice/, .run/logs/, .run/benchmarks/,
     fludb.db and the flusort_* files in source/, so the next run starts clean.
     .run/run_logs/ and .run/reports/ are kept, so run history persists.

There are two ways to trigger it:

  snakemake --cores 8 snapshot_clean
      Right now, whatever state the workspace is in (rule `snapshot_clean`).

  snakemake --cores 8 --configfile config/snapshot_clean.yaml
  (or: snakemake --cores 8 --config snapshot_clean=true)
      At the end of a full build, after every tree and the surveillance
      report are finished (rule `snapshot_clean_after_build`).

This file is included from the Snakefile after reports.smk, because the
after-build rule waits for the surveillance report (surveillance_report_targets).
"""


def snapshot_clean_targets(wildcards):
    """
    The completion marker for `rule all` to request when the run was started
    with --config snapshot_clean=true; an empty list otherwise.
    """
    if config.get("snapshot_clean", False):
        return "snapshots/snapshot_clean.done"
    return []


# Snapshot and clean right now.
# The rule has no output, so asking for it by name runs it every time, even
# when snapshots/snapshot_clean.done already exists. There is no log:
# directive because the script itself deletes .run/logs/.
rule snapshot_clean:
    """
    Create a timestamped snapshot and clean the workspace immediately.
    """
    shell:
        "bash scripts/snapshot_clean.sh"


# Snapshot and clean after a full build (--config snapshot_clean=true).
# Its inputs are the build's final outputs, so it always runs last; the
# completion marker lets `rule all` depend on it, and because the marker is
# older than the outputs of any later build, it runs again after that build.
rule snapshot_clean_after_build:
    input:
        # Segment builds
        expand("auspice/{subtype}/{segment}_tip-frequencies.json",
               subtype=["h3n2", "h1n1", "vic"],
               segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("auspice/{subtype}/{segment}.json",
               subtype=["h3n2", "h1n1", "vic"],
               segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        # Genome builds
        expand("auspice/{subtype}/genome_tip-frequencies.json",
               subtype=["h3n2", "h1n1", "vic"]),
        expand("auspice/{subtype}/genome.json",
               subtype=["h3n2", "h1n1", "vic"]),
        # The surveillance report (unless switched off), so it is archived too
        surveillance_report_targets
    output:
        touch("snapshots/snapshot_clean.done")
    shell:
        "bash scripts/snapshot_clean.sh"
