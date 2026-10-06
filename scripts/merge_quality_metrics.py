"""
Merge Nextclade QC metrics (overall score/status, coverage) into a segment's
clade-annotated metadata.

Called by the `merge_quality_metrics` rule in
workflow/snakemake_rules/segments.smk via `script:`; the `snakemake` object
is injected by Snakemake at runtime.
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
log = logging.getLogger("merge_quality_metrics")


def _log_uncaught(exc_type, exc_value, exc_tb):
    log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _log_uncaught

log.info("subtype=%s segment=%s", snakemake.wildcards.subtype, snakemake.wildcards.segment)

# Load the metadata and nextclade data
metadata_df = pd.read_csv(snakemake.input.metadata, sep="\t")
log.info("Loaded %d metadata rows from %s", len(metadata_df), snakemake.input.metadata)

nextclade_df = pd.read_csv(
    snakemake.input.nextclade,
    sep="\t",
    usecols=["seqName", "qc.overallScore", "qc.overallStatus", "coverage"],
)
log.info("Loaded %d Nextclade rows from %s", len(nextclade_df), snakemake.input.nextclade)

# Perform the merge operation, merging on the seqName
merged_df = pd.merge(metadata_df, nextclade_df, left_on="seqName", right_on="seqName", how="left")

# Rename the columns to remove the period
merged_df.rename(
    columns={
        "qc.overallScore": "qc_overallScore",
        "qc.overallStatus": "qc_overallStatus",
    },
    inplace=True,
)

# Drop the merge columns (seqName_x and seqName_y) if they exist
merged_df.drop(columns=["seqName_x", "seqName_y"], inplace=True, errors="ignore")

# QC summary - these columns drive the augur_filter query downstream
n_matched = merged_df["qc_overallStatus"].notna().sum()
log.info("%d/%d metadata rows matched a Nextclade QC record", n_matched, len(merged_df))
status_counts = merged_df["qc_overallStatus"].value_counts(dropna=False).to_dict()
log.info("qc_overallStatus counts: %s", status_counts)
log.info(
    "Rows passing coverage >= 0.9: %d",
    (pd.to_numeric(merged_df["coverage"], errors="coerce") >= 0.9).sum(),
)
if n_matched == 0:
    log.warning("No rows matched Nextclade QC: check seqName naming")

# Save the merged dataframe to the output file
merged_df.to_csv(snakemake.output.metadata_merged, sep="\t", index=False)
log.info("Wrote %s", snakemake.output.metadata_merged)
