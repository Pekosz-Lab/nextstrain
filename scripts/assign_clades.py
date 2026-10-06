"""
Append Nextclade HA clade calls to a segment's metadata.

Called by the `assign_clades` rule in workflow/snakemake_rules/segments.smk
via `script:`; the `snakemake` object is injected by Snakemake at runtime.
"""
import logging
import sys

import pandas as pd

# --- logging setup: everything (info, pandas warnings, tracebacks) -> {log} ---
logging.basicConfig(
    filename=snakemake.log[0],
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logging.captureWarnings(True)
log = logging.getLogger("assign_clades")


def _log_uncaught(exc_type, exc_value, exc_tb):
    log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _log_uncaught

log.info("subtype=%s segment=%s", snakemake.wildcards.subtype, snakemake.wildcards.segment)

# --- merge ---
metadata_df = pd.read_csv(snakemake.input.metadata, sep="\t")
log.info("Loaded %d metadata rows from %s", len(metadata_df), snakemake.input.metadata)

clade_df = pd.read_csv(
    snakemake.input.ha_clade,
    sep="\t",
    usecols=["seqName", "clade", "subclade", "legacy-clade"],
)
log.info("Loaded %d Nextclade HA rows from %s", len(clade_df), snakemake.input.ha_clade)

merged_df = pd.merge(metadata_df, clade_df, left_on="sample_ID", right_on="seqName", how="left")

n_matched = merged_df["clade"].notna().sum()
log.info("%d/%d metadata rows matched an HA clade call", n_matched, len(merged_df))
if n_matched == 0:
    log.warning("No rows matched an HA clade: check sample_ID vs seqName naming")
if len(merged_df) != len(metadata_df):
    log.warning(
        "Row count changed during merge (%d -> %d): duplicate seqName in Nextclade output?",
        len(metadata_df), len(merged_df),
    )

merged_df.to_csv(snakemake.output.metadata_clade, sep="\t", index=False)
log.info("Wrote %s", snakemake.output.metadata_clade)
