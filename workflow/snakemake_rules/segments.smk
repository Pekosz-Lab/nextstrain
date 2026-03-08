# define home dir
data_dir = config.get("data_dir", "data")

rule fetch_hana_datasets:
    priority: 1
    message: "Downloading updated Nextclade datasets"
    log: 
        "logs/nextclade_fetch_datasets.txt"
    output:
        touch("logs/fetch_hana_datasets.flag")
    shell:
        """
        echo "Clearing Nextclade dataset directories..."
        for dir in \
            nextclade/flu/h3n2/ha \
            nextclade/flu/h1n1/ha \
            nextclade/flu/vic/ha \
            nextclade/flu/h3n2/na \
            nextclade/flu/h1n1/na \
            nextclade/flu/vic/na; do
            mkdir -p $dir
            rm -rf $dir/*
        done

        echo "Downloading updated Nextclade datasets..."
        nextclade dataset get -n flu_h3n2_ha -o nextclade/flu/h3n2/ha
        nextclade dataset get -n flu_h1n1pdm_ha -o nextclade/flu/h1n1/ha
        nextclade dataset get -n flu_vic_ha -o nextclade/flu/vic/ha

        nextclade dataset get -n flu_h3n2_na -o nextclade/flu/h3n2/na
        nextclade dataset get -n flu_h1n1pdm_na -o nextclade/flu/h1n1/na
        nextclade dataset get -n flu_vic_na -o nextclade/flu/vic/na
        """

rule nextclade:
    message: "Running nextclade for {input.fasta}"
    input:
        fasta=f"{data_dir}/{{subtype}}/{{segment}}/sequences.fasta",
        ha_dir="nextclade/flu/{subtype}/ha",
        na_dir="nextclade/flu/{subtype}/na",
        dataset_ready = "logs/fetch_hana_datasets.flag" #order placeholder
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
    message: "Appending clade data"
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
        clade_df = pd.read_csv(input.ha_clade, sep='\t', usecols=['seqName', 'clade', 'subclade', "legacy-clade"])

        merged_df = pd.merge(metadata_df, clade_df, left_on='sample_ID', right_on='seqName', how='left')

        merged_df.to_csv(output.metadata_clade, sep='\t', index=False)


rule get_glycosylation:
    message: "Getting glycosylation info"
    input:
        nextclade_tsv="results/{subtype}/{segment}/nextclade.tsv"
    output:
        nextclade_tsv_with_gly="results/{subtype}/{segment}/nextclade_with_gly.txt.flag"
    log:
        "logs/get-glycosylation-clades_{subtype}_{segment}.txt"
    run:
        import pandas as pd
        import ast


        nextclade_df = pd.read_csv(input.nextclade_tsv, sep='\t')

        # if 'glycosylation' in nextclade_df.columns:
        #     for row in nextclade_df.index:
        #         if pd.isna(nextclade_df.loc[row, 'glycosylation']) or nextclade_df.loc[row, 'glycosylation'] == "":
        #             continue
        #         else:
        #             gly_lst = nextclade_df.loc[row, 'glycosylation'].split(';')
        #             gly_dict = {}
        #             for gly in gly_lst:
        #                 protein_type = gly.split(':')[0] 
        #                 site_mod_info = gly.split(':')[1] + '_' + gly.split(':')[2]

        #                 if protein_type not in gly_dict.keys():
        #                     gly_dict[protein_type] = [site_mod_info]
        #                 else:
        #                     gly_dict[protein_type].append(site_mod_info)
        #             for protein in gly_dict.keys():
        #                 gly_lst_individual = gly_dict[protein]
        #                 # gly_lst_root = fake_root_gly[protein]

        #                 # list of glycosylation sites on sequence
        #                 total_gly = gly_lst_individual.copy()
        #                 total_gly.sort()
        #                 total_gly_col_name = protein + '_glycosylation_sites_total'
        #                 nextclade_df.loc[row, total_gly_col_name] = str(total_gly)
        #                 # count of glycosylation sites on sequence
        #                 total_gly_count = len(gly_lst_individual)
        #                 total_gly_count_col_name = protein + '_glycosylation_sites_total_count'
        #                 nextclade_df.loc[row, total_gly_count_col_name] = (int(total_gly_count))
        #             if 'HA1' in gly_dict.keys():
        #                 if 'HA2' in gly_dict.keys():
        #                     nextclade_df.loc[row, 'HA_glycosylation_sites_total'] = str(ast.literal_eval(nextclade_df.loc[row, 'HA1_glycosylation_sites_total']) + ast.literal_eval(nextclade_df.loc[row, 'HA2_glycosylation_sites_total']))
        #                     nextclade_df.loc[row, 'HA_glycosylation_sites_total_count'] = int(int(nextclade_df.loc[row, 'HA1_glycosylation_sites_total_count']) + int(nextclade_df.loc[row, 'HA2_glycosylation_sites_total_count']))
        #                 else:
        #                     nextclade_df.loc[row, 'HA_glycosylation_sites_total'] = str(nextclade_df.loc[row, 'HA1_glycosylation_sites_total'])
        #                     nextclade_df.loc[row, 'HA_glycosylation_sites_total_count'] = (int(nextclade_df.loc[row, 'HA1_glycosylation_sites_total_count']))
        #             elif 'HA2' in gly_dict.keys():
        #                 nextclade_df.loc[row, 'HA_glycosylation_sites_total'] = str(nextclade_df.loc[row, 'HA2_glycosylation_sites_total'])
        #                 nextclade_df.loc[row, 'HA_glycosylation_sites_total_count'] = (int(nextclade_df.loc[row, 'HA2_glycosylation_sites_total_count']))
        #             else:
        #                 continue
                        
        # nextclade_df.to_csv(output.nextclade_tsv_with_gly, sep='\t', index=False)
        nextclade_df.to_csv(input.nextclade_tsv, sep='\t', index=False)
        with open(output.nextclade_tsv_with_gly, 'w') as file:
            file.write('glycosylation processed')



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

        metadata_df = pd.read_csv(input.metadata, sep='\t')

        cols_to_merge = ['seqName', 'qc.overallScore', 'qc.overallStatus', 'coverage']

        # if wildcards.segment == 'na':
        #     cols_to_merge += ['NA_glycosylation_sites_total', 'NA_glycosylation_sites_total_count']
        # if wildcards.segment == 'ha':
        #     cols_to_merge += ['HA1_glycosylation_sites_total', 'HA1_glycosylation_sites_total_count', 'HA2_glycosylation_sites_total', 'HA2_glycosylation_sites_total_count', 'HA_glycosylation_sites_total', 'HA_glycosylation_sites_total_count']


        nextclade_df = pd.read_csv(input.nextclade, sep='\t', usecols=cols_to_merge)

        merged_df = pd.merge(metadata_df, nextclade_df, left_on='seqName', right_on='seqName', how='left')

        merged_df.rename(columns={
            'qc.overallScore': 'qc_overallScore',
            'qc.overallStatus': 'qc_overallStatus'
        }, inplace=True)

        merged_df.drop(columns=['seqName_x', 'seqName_y'], inplace=True, errors='ignore')

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

rule write_ancestral_fasta:
    message: "Writing ancestral nucleotide sequences to FASTA"
    input:
        nt_node_data = rules.infer_ancestral.output.ancestral
    output:
        fasta = "results/{subtype}/{segment}/ancestral_sequences.fasta"
    log:
        "logs/write_ancestral_fasta_{subtype}_{segment}.txt"
    run:
        import json

        with open(input.nt_node_data) as f:
            data = json.load(f)

        with open(output.fasta, "w") as out:
            for node_name, node_info in data["nodes"].items():
                if "sequence" in node_info:
                    out.write(f">{node_name}\n")
                    out.write(node_info["sequence"] + "\n")
rule nextclade_ancestral:
    message: "Running Nextclade on ancestral sequences"
    input:
        fasta = rules.write_ancestral_fasta.output.fasta,
        dataset_ready = "logs/fetch_hana_datasets.flag"
    output:
        tsv = "results/{subtype}/{segment}/nextclade_ancestral.tsv"
    params:
        dataset = "nextclade/flu/{subtype}/{segment}/"
    log:
        "logs/nextclade_ancestral_{subtype}_{segment}.txt"
    shell:
        """
        nextclade run \
            -D {params.dataset} \
            --output-tsv {output.tsv} \
            {input.fasta} | tee {log}
        """

rule ancestral_glycosylation_to_node_data:
    message: "Converting ancestral glycosylation TSV to node-data JSON"
    input:
        tsv = rules.nextclade_ancestral.output.tsv
    output:
        json = "results/{subtype}/{segment}/glycosylation_ancestral.json"
    run:
        import pandas as pd
        import json

        df = pd.read_csv(input.tsv, sep="\t")

        node_data = {"nodes": {}}

        for _, row in df.iterrows():
            node = row["seqName"]

            glyco = row.get("glycosylation", "")

            if pd.isna(glyco) or glyco == "":
                sites = []
            else:
                gly_lst = glyco.split(";")
                sites = []
                for g in gly_lst:
                    parts = g.split(":")
                    if len(parts) >= 3:
                        protein = parts[0]
                        site = parts[1] + "_" + parts[2]
                        if protein.lower() == "na":
                            sites.append(site)

            node_data["nodes"][node] = {
                "NA_glycosylation_sites_total": {
                    "value": ",".join(sorted(sites))
                },
                "NA_glycosylation_sites_total_count": {
                    "value": len(sites)
                }
            }

        with open(output.json, "w") as out:
            json.dump(node_data, out)



# rule glycosylation_root_compare:
#     message: "Comparing glycosylation sites to root for {wildcards.segment}"
#     input:
#         ancestral_json=rules.translate.output.aa_muts,
#         nextclade_tsv=rules.nextclade.output.nextclade_tsv
#     output:
#         gly_gain="results/{subtype}/{segment}/glycosylation_gain.json",
#         gly_loss="results/{subtype}/{segment}/glycosylation_loss.json",
#         gly_net="results/{subtype}/{segment}/glycosylation_net.json"
#     run:
#         import pandas as pd
#         import json

#         segment = wildcards.segment.upper()

#         if segment not in ["HA", "NA"]:
#             with open(output.gly_gain, "w") as f:
#                 json.dump({"nodes": {}}, f)
#             with open(output.gly_loss, "w") as f:
#                 json.dump({"nodes": {}}, f)
#             with open(output.gly_net, "w") as f:
#                 json.dump({"nodes": {}}, f)
#             print(f"No glycosylation info for segment {segment}, skipped.")
#             return

#         with open(input.ancestral_json) as f:
#             aa_node_data = json.load(f)

#         node_dict = aa_node_data["nodes"]

#         root_id = None
#         for name, data in node_dict.items():
#             if "parent" not in data:
#                 root_id = name
#                 break
#         if root_id is None:
#             raise ValueError("Could not determine root node.")

#         tip_gly = pd.read_csv(input.nextclade_tsv, sep="\t")
#         if "glycosylation" not in tip_gly.columns:
#             raise ValueError("No 'glycosylation' column found in nextclade.tsv")

#         def parse_glyco_string(gly_string, segment):
#             if pd.isna(gly_string) or gly_string == "":
#                 return []

#             sites = []
#             entries = gly_string.split(";")

#             for entry in entries:
#                 parts = entry.split(":")
#                 if len(parts) == 3 and parts[0].upper().startswith(segment):
#                     seg = parts[0]
#                     position = parts[1]
#                     motif = parts[2]
#                     sites.append(f"{seg}_{position}_{motif}")

#             return sites


#         root_row = tip_gly[tip_gly["seqName"] == root_id]
#         if root_row.empty:
#             raise ValueError(f"Root '{root_id}' not found in nextclade.tsv")
#         root_gly = parse_glyco_string(root_row["glycosylation"].values[0], segment)

#         gly_gain_json = {"nodes": {}}
#         gly_loss_json = {"nodes": {}}
#         gly_net_json = {"nodes": {}}

#         for _, row in tip_gly.iterrows():
#             node_name = row["seqName"]
#             node_gly = parse_glyco_string(row["glycosylation"], segment)

#             gained = [site for site in node_gly if site not in root_gly]
#             lost = [site for site in root_gly if site not in node_gly]

#             attr_gain = f"{segment}_glycosylation_gain"
#             attr_loss = f"{segment}_glycosylation_loss"
#             attr_gain_count = f"{segment}_glycosylation_gain_count"
#             attr_loss_count = f"{segment}_glycosylation_loss_count"

#             gly_gain_json["nodes"][node_name] = {
#                 attr_gain: ",".join(gained),
#                 attr_gain_count: len(gained)
#             }

#             gly_loss_json["nodes"][node_name] = {
#                 attr_loss: ",".join(lost),
#                 attr_loss_count: len(lost)
#             }

#             attr_net_count = f"{segment}_glycosylation_net_change"
            
#             gly_net_json["nodes"][node_name] = {
#                 attr_net_count: '+' + str(len(gained)) + '/-' + str(len(lost))
#             }


#         with open(output.gly_gain, "w") as f:
#             json.dump(gly_gain_json, f, indent=2)

#         with open(output.gly_loss, "w") as f:
#             json.dump(gly_loss_json, f, indent=2)

#         with open(output.gly_net, "w") as f:
#             json.dump(gly_net_json, f, indent=2)

rule glycosylation_root_compare:
    message: "Comparing glycosylation sites to root for {wildcards.segment}"
    input:
        ancestral_json=rules.translate.output.aa_muts,
        nextclade_tsv=rules.nextclade.output.nextclade_tsv
    output:
        gly_gain="results/{subtype}/{segment}/glycosylation_gain.json",
        gly_loss="results/{subtype}/{segment}/glycosylation_loss.json",
        gly_net="results/{subtype}/{segment}/glycosylation_net.json"
    run:
        import pandas as pd
        import json

        segment = wildcards.segment.upper()

        if segment not in ["HA", "NA"]:
            with open(output.gly_gain, "w") as f:
                json.dump({"nodes": {}}, f)
            with open(output.gly_loss, "w") as f:
                json.dump({"nodes": {}}, f)
            with open(output.gly_net, "w") as f:
                json.dump({"nodes": {}}, f)
            print(f"No glycosylation info for segment {segment}, skipped.")
            return

        with open(input.ancestral_json) as f:
            aa_node_data = json.load(f)

        node_dict = aa_node_data["nodes"]

        root_id = None
        for name, data in node_dict.items():
            if "parent" not in data:
                root_id = name
                break
        if root_id is None:
            raise ValueError("Could not determine root node.")

        tip_gly = pd.read_csv(input.nextclade_tsv, sep="\t")
        if "glycosylation" not in tip_gly.columns:
            raise ValueError("No 'glycosylation' column found in nextclade.tsv")

        def parse_glyco_string(gly_string, segment):
            if pd.isna(gly_string) or gly_string == "":
                return None

            sites = []
            entries = gly_string.split(";")

            for entry in entries:
                parts = entry.split(":")
                if len(parts) == 3 and parts[0].upper().startswith(segment):
                    seg = parts[0]
                    position = parts[1]
                    motif = parts[2]
                    sites.append(f"{seg}_{position}_{motif}")

            return sites


        root_row = tip_gly[tip_gly["seqName"] == root_id]
        if root_row.empty:
            raise ValueError(f"Root '{root_id}' not found in nextclade.tsv")

        root_gly = parse_glyco_string(root_row["glycosylation"].values[0], segment)

        gly_gain_json = {"nodes": {}}
        gly_loss_json = {"nodes": {}}
        gly_net_json = {"nodes": {}}

        for _, row in tip_gly.iterrows():
            node_name = row["seqName"]
            node_gly = parse_glyco_string(row["glycosylation"], segment)

            attr_gain = f"{segment}_glycosylation_gain"
            attr_loss = f"{segment}_glycosylation_loss"
            attr_gain_count = f"{segment}_glycosylation_gain_count"
            attr_loss_count = f"{segment}_glycosylation_loss_count"
            attr_net_count = f"{segment}_glycosylation_net_change"

            # HANDLE MISSING GLYCOSYLATION DATA
            if node_gly is None:
                gly_gain_json["nodes"][node_name] = {
                    attr_gain: "NA",
                    attr_gain_count: None
                }

                gly_loss_json["nodes"][node_name] = {
                    attr_loss: "NA",
                    attr_loss_count: None
                }

                gly_net_json["nodes"][node_name] = {
                    attr_net_count: "NA"
                }

                continue

            gained = [site for site in node_gly if site not in root_gly]
            lost = [site for site in root_gly if site not in node_gly]

            gly_gain_json["nodes"][node_name] = {
                attr_gain: ",".join(gained),
                attr_gain_count: len(gained)
            }

            gly_loss_json["nodes"][node_name] = {
                attr_loss: ",".join(lost),
                attr_loss_count: len(lost)
            }

            gly_net_json["nodes"][node_name] = {
                attr_net_count: '+' + str(len(gained)) + '/-' + str(len(lost))
            }


        with open(output.gly_gain, "w") as f:
            json.dump(gly_gain_json, f, indent=2)

        with open(output.gly_loss, "w") as f:
            json.dump(gly_loss_json, f, indent=2)

        with open(output.gly_net, "w") as f:
            json.dump(gly_net_json, f, indent=2)


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
        auspice_config="config/{subtype}/auspice_config.json",
        gly_gain=lambda wildcards: f"results/{wildcards.subtype}/{wildcards.segment}/glycosylation_gain.json",
        gly_loss=lambda wildcards: f"results/{wildcards.subtype}/{wildcards.segment}/glycosylation_loss.json",
        gly_net=lambda wildcards: f"results/{wildcards.subtype}/{wildcards.segment}/glycosylation_net.json"
    output:
        auspice_json="auspice/{subtype}/{segment}.json"
    params:
        colors="config/{subtype}/colors.tsv",
        node_data=lambda wildcards, input: " ".join(
            f for f in [
                input.branch_lengths,
                input.traits,
                input.nt_muts,
                input.aa_muts,
                input.vaccine,
                input.gly_gain if os.path.exists(input.gly_gain) else None,
                input.gly_loss if os.path.exists(input.gly_loss) else None,
                input.gly_net if os.path.exists(input.gly_net) else None
            ] if f is not None
        )
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
            --include-internal-nodes \
            --metadata {input.metadata} \
            --metadata-id-columns sample_ID \
            --output {output.frequencies}
        """