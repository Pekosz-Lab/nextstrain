import os
import datetime
import pandas as pd
from treetime.utils import numeric_date

wildcard_constraints:
    subtype = "h1n1|h3n2|vic", # reduce if builds for specific subtypes are desired
    segment = "pb2|pb1|pa|ha|np|na|mp|ns" # reduce if builds for specific segments are desired

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

data_dir = config.get("data_dir", "data")

rule all:
    input:
        # Metadata outputs
        expand("results/{subtype}/{segment}/metadata.tsv", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("results/{subtype}/{segment}/metadata_merged.tsv", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("results/{subtype}/{segment}/filtered.tsv", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        
        # Filtered and aligned sequences
        expand("results/{subtype}/{segment}/filtered.fasta", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("results/{subtype}/{segment}/aligned.fasta", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        
        # Tree and node data outputs
        expand("results/{subtype}/{segment}/tree_raw.nwk", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("results/{subtype}/{segment}/tree.nwk", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("results/{subtype}/{segment}/branch_lengths.json", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("results/{subtype}/{segment}/traits.json", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("results/{subtype}/{segment}/nt_muts.json", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("results/{subtype}/{segment}/aa_muts.json", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        
        # Auspice JSON outputs for visualization
        expand("auspice/{subtype}/{segment}_tip-frequencies.json", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]),
        expand("auspice/{subtype}/{segment}.json", subtype=["h3n2", "h1n1", "vic"], segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"])

rule fetch_HANA_datasets:
    message: "Downloading updated nextclade datasets"
    output:
        ha_dir="nextclade/flu/{subtype}/ha",
        na_dir="nextclade/flu/{subtype}/na"
    params:
        datasets={
            "h3n2": ["flu_h3n2_ha", "flu_h3n2_na"],
            "h1n1": ["flu_h1n1pdm_ha", "flu_h1n1pdm_na"],
            "vic": ["flu_vic_ha", "flu_vic_na"]
        },
        temp_dir="temp_datasets"  # Temporary location for new dataset downloads
    run:
        import subprocess
        import shutil

        datasets = params.datasets[wildcards.subtype]

        for dataset in datasets:
            temp_output_dir = os.path.join(params.temp_dir, dataset.split('_')[-1])
            os.makedirs(params.temp_dir, exist_ok=True)

            subprocess.run(["nextclade", "dataset", "get", "-n", dataset, "-o", temp_output_dir])

            target_name = 'ha' if 'ha' in dataset else 'na'
            target_dir = output.ha_dir if target_name == 'ha' else output.na_dir

            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            shutil.move(temp_output_dir, target_dir)

        shutil.rmtree(params.temp_dir)

rule nextclade:
    message: "Running nextclade for {input.fasta}"
    input:
        fasta=f"{data_dir}/{{subtype}}/{{segment}}/sequences.fasta",
        ha_dir="nextclade/flu/{subtype}/ha",
        na_dir="nextclade/flu/{subtype}/na"
    output:
        nextclade_tsv="results/{subtype}/{segment}/nextclade.tsv",
        nextclade_fasta="results/{subtype}/{segment}/nextclade.aligned.fasta"
    log: 
        "logs/nextclade_{subtype}_{segment}.txt"
    params:
        dataset="nextclade/flu/{subtype}/{segment}/"
    run:
        shell(
            f"nextclade run "
            f"-D {params.dataset} "
            f"--output-fasta {output.nextclade_fasta} "
            f"--output-tsv {output.nextclade_tsv} "
            f"{input.fasta}" 
            f"| tee {log}"
        )

rule assign_clades:
    message: "Appending clade data "
    input:
        metadata="data/{subtype}/{segment}/metadata.tsv",
        ha_clade="results/{subtype}/ha/nextclade.tsv"
    output:
        metadata_clade="results/{subtype}/{segment}/metadata.tsv"
    log: 
        "logs/assign-clades_{subtype}_{segment}.txt"
    run:
        import pandas as pd

        metadata_df = pd.read_csv(input.metadata, sep='\t')
        clade_df = pd.read_csv(input.ha_clade, sep='\t', usecols=['seqName', 'clade', 'subclade'])

        merged_df = pd.merge(metadata_df, clade_df, left_on='sample_ID', right_on='seqName', how='left')

        merged_df.to_csv(output.metadata_clade, sep='\t', index=False)

rule merge_quality_metrics:
    input:
        metadata=rules.assign_clades.output.metadata_clade,  # "results/{subtype}/{segment}/metadata_clade.tsv"
        nextclade="results/{subtype}/{segment}/nextclade.tsv"
    output:
        metadata_merged="results/{subtype}/{segment}/metadata_merged.tsv"
    log: 
        "logs/merge_quality_metrics-{subtype}_{segment}.txt"
    run:
        import pandas as pd

        # Load the metadata and nextclade data
        metadata_df = pd.read_csv(input.metadata, sep='\t')
        nextclade_df = pd.read_csv(input.nextclade, sep='\t', usecols=['seqName', 'qc.overallScore', 'qc.overallStatus', 'coverage'])

        # Perform the merge operation, merging on the seqName
        merged_df = pd.merge(metadata_df, nextclade_df, left_on='seqName', right_on='seqName', how='left')

        # Rename the columns to remove the period
        merged_df.rename(columns={
            'qc.overallScore': 'qc_overallScore',
            'qc.overallStatus': 'qc_overallStatus'
        }, inplace=True)

        # Drop the merge columns (seqName_x and seqName_y) if they exist
        merged_df.drop(columns=['seqName_x', 'seqName_y'], inplace=True, errors='ignore')

        # Save the merged dataframe to the output file
        merged_df.to_csv(output.metadata_merged, sep='\t', index=False)

    
rule augur_filter:
    input:
        sequences="data/{subtype}/{segment}/sequences.fasta",
        metadata= rules.merge_quality_metrics.output.metadata_merged #"results/{subtype}/{segment}/metadata_merged.tsv"
    output:
        filtered_sequences="results/{subtype}/{segment}/filtered.fasta",
        filtered_metadata="results/{subtype}/{segment}/filtered.tsv"
    params:
        min_length=lambda wildcards: min_lengths.get(wildcards.segment, 0),  # Get min length for the segment
        exclude="config/exclude.tsv" # manually pruned for sequences outside of molecular clock bounds.
    log:
        "logs/augur_filter_{subtype}_{segment}.txt"
    shell:
        """
        augur filter \
            --sequences {input.sequences} \
            --metadata {input.metadata} \
            --query "(coverage >= 0.9) & ((qc_overallStatus == 'good') | (qc_overallStatus == 'mediocre'))" \
            --min-length {params.min_length} \
            --exclude {params.exclude} \
            --metadata-id-columns sample_ID \
            --output-sequences {output.filtered_sequences} \
            --output-metadata {output.filtered_metadata} | tee {log}
        """

rule align:
    message:
        """
        Aligning sequences to {input.reference}
        """
    input:
        filtered_sequences="results/{subtype}/{segment}/filtered.fasta",
        reference="config/{subtype}/reference_{segment}.gb"
    output:
        aligned_sequences="results/{subtype}/{segment}/aligned.fasta"
    params:
        nthreads=8
    log:
        "logs/align_{subtype}_{segment}.txt"
    shell:
        """
        augur align \
            --sequences {input.filtered_sequences} \
            --nthreads {params.nthreads} \
            --reference-sequence {input.reference} \
            --remove-reference \
            --output {output.aligned_sequences} \
            --fill-gaps | tee {log}
        """

rule raw_tree:
    message: "Building raw trees"
    input:
        alignment=rules.align.output.aligned_sequences
    output:
        tree="results/{subtype}/{segment}/tree_raw.nwk"
    shell:
        """
        augur tree \
            --alignment {input.alignment} \
            --output {output.tree} | tee {log}
        """

# TODO: identify more rigorous rates for h3n2 mp,ns h1n1 mp and vic mp,ns. 

def clock_rate(w):
    # Define clock rates for specific subtype and segment combinations
    # rates with "# *" " = Derived from 12y runs - https://github.com/nextstrain/seasonal-flu/blob/9a77301b4f9c58a8e948b0f7231134fcc3fe39b8/workflow/snakemake_rules/core
    rate = {
        #h3n2 rates
        ('h3n2', 'pb2'): 0.00218, # *
        ('h3n2', 'pb1'): 0.00139 , # *
        ('h3n2', 'pa'): 0.00178 , # *
        ('h3n2', 'ha'): 0.00382 , # *
        ('h3n2', 'np'): 0.00157 , # *
        ('h3n2', 'na'): 0.00267 , # *
        ('h3n2', 'mp'): 0.00381 , # source: https://www.nature.com/articles/s41598-022-20179-7/tables/2
        ('h3n2', 'ns'): 0.00454 , # source: https://www.nature.com/articles/s41598-022-20179-7/tables/2
        #h1n1 
        ('h1n1', 'pb1'): 0.00205, # *
        ('h1n1', 'pb2'): 0.00277, # *
        ('h1n1', 'pa'): 0.00217, # *
        ('h1n1', 'ha'): 0.00381, # ** ; source: 12y https://nextstrain.org/seasonal-flu/h1n1pdm/ha/12y?l=clock
        ('h1n1', 'np'): 0.00221, # *
        ('h1n1', 'na'): 0.00326, # *
        ('h1n1', 'mp'): 0.00207, # *; source: 30y egg enriched https://nextstrain.org/groups/blab/h1n1pdm/30y/egg/mp?l=clock
        ('h1n1', 'ns'): 0.00339, # *
        #vic
        ('vic', 'pb2'): 0.00106, # *
        ('vic', 'pb1'): 0.00114, # *
        ('vic', 'pa'): 0.00178, # *
        ('vic', 'ha'): 0.00145, # *
        ('vic', 'np'): 0.00132, # *
        ('vic', 'na'): 0.00133, # *
        ('vic', 'mp'): 0.00108, # source: https://nextstrain.org/groups/blab/vic/30y/egg/mp
        ('vic', 'ns'): 0.00104, # source: https://nextstrain.org/groups/blab/vic/30y/egg/ns?l=clock
    }
    # Get the rate for the given subtype and segment, or return a default value if not specified
    return rate.get((w.subtype, w.segment), 0.001)  # Default rate if not found

def clock_std_dev(w):
    # Return standard deviation based on the clock rate (clock_rate / 5)
    return clock_rate(w) / 5

rule refine:
    message:
        """
        Refining tree
          - estimate timetree
          - use {params.coalescent} coalescent timescale
          - estimate {params.date_inference} node dates
          - filter tips more than {params.clock_filter_iqd} IQDs from clock expectation
        """
    input:
        tree = rules.raw_tree.output.tree,  # Use the raw tree output from the previous rule
        alignment = "results/{subtype}/{segment}/aligned.fasta",
        metadata = "results/{subtype}/{segment}/filtered.tsv"
    output:
        tree = "results/{subtype}/{segment}/tree.nwk",
        node_data = "results/{subtype}/{segment}/branch_lengths.json"
    params:
        coalescent = "opt",
        date_inference = "marginal",
        clock_filter_iqd = 4,
        clock_rate = clock_rate,  # Function reference to calculate clock rate dynamically
        clock_std_dev = clock_std_dev  # Function reference to calculate clock std dev dynamically
    log:
        "logs/refine_{subtype}_{segment}.txt"
    shell:
        """
        # Run augur refine with conditional clock-rate and clock-std-dev arguments
        augur refine \
            --tree {input.tree} \
            --alignment {input.alignment} \
            --metadata {input.metadata} \
            --metadata-id-columns sample_ID \
            --output-tree {output.tree} \
            --output-node-data {output.node_data} \
            --timetree \
            --coalescent {params.coalescent} \
            --date-confidence \
            --date-inference {params.date_inference} \
            --clock-filter-iqd {params.clock_filter_iqd} \
            --clock-rate {params.clock_rate}  \
            --clock-std-dev {params.clock_std_dev} | tee {log}
        """

rule annotate_traits:
    message: "Annotating traits"
    input:
        tree = rules.refine.output.tree,
        metadata = rules.augur_filter.output.filtered_metadata,
    output:
        traits = "results/{subtype}/{segment}/traits.json"
    params:
        columns=["clade", "subclade", "qc_overallStatus", "qc_overallScore", "coverage", "sequencing_run"]
    log: 
        "logs/annotate_traits_{subtype}_{segment}.txt"
    shell:
        """
        augur traits \
            --tree {input.tree} \
            --metadata {input.metadata} \
            --metadata-id-columns sample_ID \
            --output-node-data {output.traits} \
            --columns {params.columns} \
            --confidence | tee {log}
        """

rule infer_ancestral:
    message: "Reconstructing ancestral sequences and mutations"
    input:
        tree = rules.refine.output.tree,
        alignment = rules.align.output.aligned_sequences
    output:
        ancestral="results/{subtype}/{segment}/nt_muts.json"
    params:
        inference="joint"  # Method for ancestral inference
    log:
        "logs/infer_ancestral_{subtype}_{segment}.txt"
    shell:
        """
        augur ancestral \
            --tree {input.tree} \
            --alignment {input.alignment} \
            --output-node-data {output.ancestral} \
            --inference {params.inference} | tee {log}
        """

rule translate:
    message: "Translate mutations"
    input:
        tree = rules.refine.output.tree,
        ancestral = rules.infer_ancestral.output.ancestral, 
        reference_sequence=lambda wildcards: f"config/{wildcards.subtype}/genome_annotation_ha.gff"
        if wildcards.segment == "ha" else f"config/{wildcards.subtype}/reference_{wildcards.segment}.gb"
    log: 
        "logs/translate_{subtype}_{segment}.txt"
    output:
        aa_muts="results/{subtype}/{segment}/aa_muts.json"
    shell:
        """
        augur translate \
            --tree {input.tree} \
            --ancestral-sequences {input.ancestral} \
            --reference-sequence {input.reference_sequence} \
            --output-node-data {output.aa_muts} | tee {log}
        """    

rule export:
    message: "Exporting auspice JSON files for {wildcards.subtype}/{wildcards.segment}"
    input:
        tree=rules.refine.output.tree,
        metadata=rules.augur_filter.output.filtered_metadata,
        description="config/description.md",
        branch_lengths=rules.refine.output.node_data,
        traits=rules.annotate_traits.output.traits,
        nt_muts=rules.infer_ancestral.output.ancestral,
        aa_muts=rules.translate.output.aa_muts,
        vaccine="config/{subtype}/vaccine.json",
        auspice_config="config/{subtype}/auspice_config.json"
    output:
        auspice_json="auspice/{subtype}/{segment}.json"
    params:
        colors="config/{subtype}/colors.tsv",
        # Concatenate all node data inputs dynamically for --node-data flag
        node_data=lambda wildcards, input: " ".join([
            input.branch_lengths,
            input.traits,
            input.nt_muts,
            input.aa_muts,
            input.vaccine
        ])
    log: 
        "logs/export_{subtype}_{segment}.txt"
    shell:
        """
        augur export v2 \
            --tree {input.tree} \
            --metadata {input.metadata} \
            --description {input.description} \
            --node-data {params.node_data} \
            --metadata-id-columns sample_ID \
            --auspice-config {input.auspice_config} \
            --output {output.auspice_json} | tee {log}
        """

rule frequency:
    message: "Calculating segment frequencies"
    input: 
        tree=rules.refine.output.tree,
        metadata=rules.augur_filter.output.filtered_metadata,
    output:
        frequencies = "auspice/{subtype}/{segment}_tip-frequencies.json"
    shell:
        """
        augur frequencies \
            --method kde \
            --tree {input.tree} \
            --narrow-bandwidth 0.25 \
            --wide-bandwidth 0.083 \
            --proportion-wide 0.0 \
            --pivot-interval 1 \
            --min-date 2020.0 \
            --max-date 2025.0 \
            --include-internal-nodes \
            --metadata {input.metadata} \
            --metadata-id-columns sample_ID \
            --output {output.frequencies}
        """
