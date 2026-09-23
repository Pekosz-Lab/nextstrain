"""
This pipeline accept 3 input sequence files in FASTA format and ingests them to 
influenza genomes filtered to "complete" only by segment and concatenated genome for nextstrain builds

Input: 
- vaccine.fasta
- JHH_sequences.fasta
- JHH_metadata.tsv

Output: 
an equivalent sequences.fasta and metadata.tsv for: 

    - genome
    - pb2
    - pb1
    - pa
    - ha
    - np
    - na
    - mp
    - ns

final output located at data/{segment OR genome}

"""

# Input locations can be overridden by a Snakemake configuration file. The
# defaults preserve the existing production workflow exactly.
source_dir = config.get("source_dir", "source")
jhh_sequences = config.get(
    "jhh_sequences",
    f"{source_dir}/JHH_sequences.fasta",
)
jhh_metadata = config.get(
    "jhh_metadata",
    f"{source_dir}/JHH_metadata.txt",
)
vaccine_sequences = config.get(
    "vaccine_sequences",
    f"{source_dir}/vaccine.fasta",
)
flusort_sequences = f"{source_dir}/flusort_JHH_sequences.fasta"
flusort_metadata = f"{source_dir}/flusort_JHH_metadata.tsv"

rule flusort:
    message: "Running flusort"
    input:
        unknown_jhh_sequences = jhh_sequences,
        unknown_jhh_metadata = jhh_metadata
    output:
        sequences = flusort_sequences,
        metadata = flusort_metadata,
        flag = touch("data/flusort_completed.flag")
    shell:
        """
        python scripts/flusort/flusort.py \
            -db scripts/flusort/blast_database/pyflute_ha_database \
            -i {input.unknown_jhh_sequences} \
            -m {input.unknown_jhh_metadata} \
            -f {output.sequences} \
            -o {output.metadata}
        """

# im sure you looked
rule fludb_inititate:
    message: "inititate fludb"
    output:
        touch("data/fludb_inititated.flag")
    shell:
        """
        python fludb/scripts/fludb_inititate.py
        """

rule upload_genomes:
    message: "upload sequences to fludb"
    input:
        sequences = flusort_sequences,
        metadata = flusort_metadata,
        fludb_init = "data/fludb_inititated.flag",
        flusort_completed = "data/flusort_completed.flag"
    output:
        touch("data/genomes_uploaded.flag")
    log:
        "logs/fludb_upload_status.txt"
    shell:
        """
        python fludb/scripts/upload_jhh.py \
            -d fludb.db \
            -f {input.sequences} \
            -m {input.metadata} \
            --require-sequence | tee {log}
        """

rule upload_vaccines:
    message: "uploading vaccine strains"
    input:
        sequences = vaccine_sequences,
        fludb_init = "data/fludb_inititated.flag",
        flusort_completed = "data/flusort_completed.flag"
    output:
        touch("data/vaccines_uploaded.flag")
    shell:
        """
        python fludb/scripts/upload_vaccine.py \
            -d fludb.db \
            -f {input.sequences}
        """

rule download_segments:
    message: "Downloading segments"
    input:
        genomes_uploaded = "data/genomes_uploaded.flag",
        vaccines_uploaded = "data/vaccines_uploaded.flag"
    output:
        pb2 = "data/{subtype}/pb2/sequences.fasta",
        pb1 = "data/{subtype}/pb1/sequences.fasta",
        pa = "data/{subtype}/pa/sequences.fasta",
        ha = "data/{subtype}/ha/sequences.fasta",
        np = "data/{subtype}/np/sequences.fasta",
        na = "data/{subtype}/na/sequences.fasta",
        mp = "data/{subtype}/mp/sequences.fasta",
        ns = "data/{subtype}/ns/sequences.fasta",
        pb2_metadata = "data/{subtype}/pb2/metadata.tsv",
        pb1_metadata = "data/{subtype}/pb1/metadata.tsv",
        pa_metadata = "data/{subtype}/pa/metadata.tsv",
        ha_metadata = "data/{subtype}/ha/metadata.tsv",
        np_metadata = "data/{subtype}/np/metadata.tsv",
        na_metadata = "data/{subtype}/na/metadata.tsv",
        mp_metadata = "data/{subtype}/mp/metadata.tsv",
        ns_metadata = "data/{subtype}/ns/metadata.tsv",
        segments_flag = touch("data/{subtype}/segments_downloaded.flag")
    shell:
        "python scripts/fludb_download_seasonal_build.py"

rule download_genomes:
    message: "Downloading genomes"
    input:
        segments_flag = "data/{subtype}/segments_downloaded.flag",
        genomes_uploaded = "data/genomes_uploaded.flag",
        vaccines_uploaded = "data/vaccines_uploaded.flag"
    output:
        genome = "data/{subtype}/genome/sequences.fasta",
        genome_metadata = "data/{subtype}/genome/metadata.tsv"
    shell:
        "python scripts/fludb_download_seasonal_build_genomes.py"

rule ingest_complete:
    message: "All ingest steps completed"
    input:
        "data/genomes_uploaded.flag"  # Ensure all ingest tasks are finished
    output:
        touch("data/ingest_completed.flag")
    shell:
        "echo 'Ingest complete'"
