"""
Sync the subclade colours with the official Nextstrain seasonal-flu builds.

The `sync_subclade_colors` rule runs scripts/sync_subclade_colors.py, which
rewrites config/{h3n2,h1n1,vic}/colors.tsv from nextstrain/seasonal-flu and
records where the colours came from in config/subclade_colors_source.tsv.

Every Auspice export (export in segments.smk, genome_export in genomes.smk)
waits for it, so whenever trees are exported they use the current official
colours. When nothing needs exporting, the sync does not run.

  Sync right now, without building:   snakemake --cores 1 sync_subclade_colors
  Skip the sync for one run:          snakemake ... --config sync_subclade_colors=false

If GitHub cannot be reached, the rule logs a warning and the build carries on
with the colours already in config/. Review `git diff config/*/colors.tsv`
after a run and commit any changes.

This file is included from the Snakefile before segments.smk and genomes.smk,
because their export rules call subclade_colors_synced().
"""

SUBCLADE_COLORS_SYNCED = ".run/subclade_colors.synced"


def subclade_colors_sync_wanted():
    """
    True unless the run was started with --config sync_subclade_colors=false.
    Values given on the command line arrive as text, so "false", "0", "no"
    and "off" all switch the sync off.
    """
    setting = str(config.get("sync_subclade_colors", True)).strip().lower()
    return setting not in ("false", "0", "no", "off")


def subclade_colors_synced(wildcards):
    """
    The sync marker for the export rules to wait on; an empty list when the
    sync is switched off.
    """
    if subclade_colors_sync_wanted():
        return SUBCLADE_COLORS_SYNCED
    return []


# One job for all three subtypes, since they share
# config/subclade_colors_source.tsv. The marker is temp(), so it is removed
# once every export has used it and the sync runs again on the next build.
rule sync_subclade_colors:
    message: "Syncing subclade colours with nextstrain/seasonal-flu"
    input:
        script = "scripts/sync_subclade_colors.py"
    output:
        marker = temp(SUBCLADE_COLORS_SYNCED)
    log:
        ".run/logs/sync_subclade_colors/sync_subclade_colors.log"
    benchmark:
        ".run/benchmarks/sync_subclade_colors/sync_subclade_colors.tsv"
    shell:
        """
        exec > {log} 2>&1
        if ! python -u {input.script} --config-dir config; then
            echo "WARNING: could not sync subclade colours; keeping config/*/colors.tsv as is"
        fi
        touch {output.marker}
        """
