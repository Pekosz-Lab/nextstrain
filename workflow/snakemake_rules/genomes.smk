# Logging: every rule writes stdout + stderr to logs/{rule}/{subtype}.log and
# records runtime / peak memory to benchmarks/{rule}/{subtype}.tsv.

rule genome_clades:
    message: "append nextclade calls to the genome"
    input:
        metadata = "data/{subtype}/genome/metadata.tsv",
        nextclade = "results/{subtype}/ha/nextclade.tsv"
    output:
        clades = "results/{subtype}/genome/nextclade.tsv"
    log:
        "logs/genome_clades/{subtype}.log"
    shell:
        """
        exec 2> {log}
        csvtk -t join -f "sequence_ID;seqName" \
            {input.metadata} \
            {input.nextclade} \
            --left-join \
            > {output.clades}
        """

min_genome_size = 13000

rule genome_filter:
    message: "filtering genomes"
    input:
        sequences = "data/{subtype}/genome/sequences.fasta",
        metadata = rules.genome_clades.output.clades
    output:
        filtered_sequences="results/{subtype}/genome/filtered.fasta",
        filtered_metadata="results/{subtype}/genome/filtered.tsv"
    params:
        min_length = min_genome_size, # Get min length for the segment - where to define genome
        exclude="config/exclude.tsv" # manually pruned for sequences outside of molecular clock bounds.
    log:
        "logs/genome_filter/{subtype}.log"
    benchmark:
        "benchmarks/genome_filter/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
        augur filter \
            --sequences {input.sequences} \
            --metadata {input.metadata} \
            --min-length {params.min_length} \
            --exclude {params.exclude} \
            --metadata-id-columns sample_ID \
            --output-sequences {output.filtered_sequences} \
            --output-metadata {output.filtered_metadata}
        """

rule genome_align:
    message: "aligning genomes"
    input:
        sequences = rules.genome_filter.output.filtered_sequences
    output:
        alignment = "results/{subtype}/genome/aligned.fasta"
    params:
        reference = "config/{subtype}/genome.gb"
    threads: 80  # upper bound; Snakemake caps this at --cores
    log:
        "logs/genome_align/{subtype}.log"
    benchmark:
        "benchmarks/genome_align/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
        augur align \
            --sequences {input.sequences} \
            --output {output.alignment} \
            --reference-sequence {params.reference} \
            --fill-gaps \
            --remove-reference \
            --nthreads {threads}
        """

rule genome_tree:
    message: "building raw tree"
    input:
        alignment = rules.genome_align.output.alignment
    output:
        tree = "results/{subtype}/genome/tree_raw.nwk"
    threads: 64  # upper bound; Snakemake caps this at --cores
    log:
        "logs/genome_tree/{subtype}.log"
    benchmark:
        "benchmarks/genome_tree/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
        augur tree \
            --nthreads {threads} \
            --alignment {input.alignment} \
            --output {output.tree}
        """

rule genome_refine:
    message: "Refining branches with treetime for {wildcards.subtype}"
    input:
        tree = rules.genome_tree.output.tree,
        metadata = rules.genome_filter.output.filtered_metadata,
        alignment = rules.genome_align.output.alignment
    output:
        refined = "results/{subtype}/genome/tree.nwk",
        nodes = "results/{subtype}/genome/branch_lengths.json"
    params:
        stdev = 0.00211,
        clock_rate = lambda wildcards: {"h3n2": 0.00272, "h1n1": 0.00272, "vic": 0.00127}[wildcards.subtype] # calculated from average of all segment rates
    log:
        "logs/genome_refine/{subtype}.log"
    benchmark:
        "benchmarks/genome_refine/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
        augur refine \
            --tree {input.tree} \
            --alignment {input.alignment} \
            --metadata {input.metadata} \
            --metadata-id-columns sample_ID \
            --output-tree {output.refined} \
            --output-node-data {output.nodes} \
            --timetree \
            --date-confidence \
            --clock-rate {params.clock_rate} \
            --clock-std-dev {params.stdev} \
            --stochastic-resolve \
            --coalescent "opt" \
            --date-inference "marginal"
        """

rule genome_traits:
    message: "annotating traits"
    input:
        tree = rules.genome_refine.output.refined,
        metadata = rules.genome_filter.output.filtered_metadata # should be fine using the same input in 2 rules from a previous rule
    output:
        node_data = "results/{subtype}/genome/traits.json"
    log:
        "logs/genome_traits/{subtype}.log"
    benchmark:
        "benchmarks/genome_traits/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
        augur traits \
        --tree {input.tree} \
        --metadata {input.metadata} \
        --metadata-id-columns sample_ID \
        --output-node-data {output.node_data} \
        --columns clade subclade
        """

rule genome_ancestral:
    message: "inferring ancestral states with treetime"
    input:
        tree = rules.genome_refine.output.refined,
        alignment = rules.genome_align.output.alignment
    output:
        nt_muts = "results/{subtype}/genome/nt_muts.json"
    log:
        "logs/genome_ancestral/{subtype}.log"
    benchmark:
        "benchmarks/genome_ancestral/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
        augur ancestral \
            --tree {input.tree} \
            --alignment {input.alignment} \
            --output-node-data {output.nt_muts} \
            --inference "joint"
        """

rule genome_translate:
    message: "translate ancestral to aa"
    input: 
        tree = rules.genome_refine.output.refined,
        nt_muts = rules.genome_ancestral.output.nt_muts
    output: 
        aa_muts = "results/{subtype}/genome/aa_muts.json"
    params:
        reference = "config/{subtype}/genome.gb"
    log:
        "logs/genome_translate/{subtype}.log"
    benchmark:
        "benchmarks/genome_translate/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
        augur translate \
            --tree {input.tree} \
            --ancestral-sequences {input.nt_muts} \
            --reference-sequence {params.reference} \
            --output-node-data {output.aa_muts}
        """    

rule genome_export:
    message: "export genome build"
    input:
        tree = rules.genome_refine.output.refined,
        metadata = rules.genome_filter.output.filtered_metadata,
        description = "config/description.md",
        branch_lengths = rules.genome_refine.output.nodes,
        traits = rules.genome_traits.output.node_data,
        nt_muts = rules.genome_ancestral.output.nt_muts,
        aa_muts = rules.genome_translate.output.aa_muts,
        config = "config/{subtype}/auspice_config.json",
        vaccine="config/{subtype}/vaccine.json"
    output:
        auspice = "auspice/{subtype}/genome.json"
    log:
        "logs/genome_export/{subtype}.log"
    benchmark:
        "benchmarks/genome_export/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
        augur export v2 \
            --tree {input.tree} \
            --metadata {input.metadata} \
            --metadata-id-columns sample_ID \
            --description {input.description} \
            --node-data \
            {input.branch_lengths} \
            {input.traits} \
            {input.nt_muts} \
            {input.aa_muts} \
            {input.vaccine} \
            --auspice-config {input.config} \
            --output {output.auspice}
        """

rule genome_frequencies:
    message: "calculating genome frequencies"
    input: 
        tree = rules.genome_refine.output.refined,
        metadata = rules.genome_filter.output.filtered_metadata
    output:
        frequencies = "auspice/{subtype}/genome_tip-frequencies.json"
    log:
        "logs/genome_frequencies/{subtype}.log"
    benchmark:
        "benchmarks/genome_frequencies/{subtype}.tsv"
    shell:
        """
        exec > {log} 2>&1
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
