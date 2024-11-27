# Pekosz Lab Seasonal Influenza Nextstrain Builds

This repository houses al scripts, snakefiles, and configuration files for the [Pekosz Lab nextstrain builds](https://nextstrain.org/groups/PekoszLab) 

Currently, 24 total builds are maintained for all 8 segments of circulaing H1N1, H3N2, and B/Vic viruses detected through the Johns Hopkins Hospital (JHH) Network supported by [JH-CEIRR](https://www.ceirr-network.org/centers/jh-ceirr). As of [2024-11-26](#history), all builds are constructed using a simplified [snakemake](https://snakemake.readthedocs.io/en/stable/) pipline.

# Getting Started with this Pipeline

## Quickstart

1. Clone this repository and setup your environment. 
2. Access genome and metadata from JHH and or GISAID. Deposit in the `source/` directory. 
3. If using JHH metadata - append type and subtype data to its respective `metadata.tsv`
   - [flusort](scripts/flusort)
4. Upload all genome and metadata to fludb. 
   - [upload_gisaid.py](fludb/scripts/upload_gisaid.py) 
   - [upload_JHH.py](fludb/scripts/upload_jhh.py)
5. Query genomes and metadata and depost in the `data/` directory.
   - [download.py](fludb/scripts/download.py)
6. Execute Snakemake file
   `snakemake --cores <number>`
7. Upload builds to nextstrain. 

## 1. Clone this repository

```shell
git clone https://github.com/Pekosz-Lab/seasonal-flu.git
```

## 2. Setup your environment

>[!WARNING]
> Dependencies for this build are maintained through `conda`. Download the latest version [here](https://anaconda.org/anaconda/conda). A breif introduction to conda and conda environments can be found [here](https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html).

Dependencies for all scripts can be built the [environment.yml](environment.yml). Navigate to your directory using `cd seasonal-flu` and execute: 

```shell
conda env create -f environment.yml
```

## 3. Access and Curate Data

>[!WARNING]
> These builds are designed to ingest influenza genome data and metadata originating from [GISAID](https://gisaid.org/) and internally from the Mostafa lab at the Johns Hopkins Hospital (JHH) network. Due to the [regulated access](https://gisaid.org/terms-of-use/) to all GISAID data, individual credentials are needed to access these data and cannot be shared publicly. Furthermore, Influenza Genomes from the JHH network accessed ahead of publishing to GISAID are private and cannot be shared publically on this repository.

A build should contain 2 types of files for each institute: 
   1. sequences.fasta 
   2. metadata.fasta

These should be placed in the `source` folder prior to [fludb](fludb/) upload

```
source/
├── GISAID_metadata.xls
├── GISAID_sequences.fasta
├── JHH_metadata.tsv
├── JHH_sequences.fasta
├── vaccines.fasta
└── vaccines.tsv
```

## Data Preparation

### 3. Append Type and Subtype Assignments to JHH Metadata using [flusort.py](scripts/flusort/flusort.py)

```shell
python scripts/flusort/flusort.py \
  -db scripts/flusort/blast_database/pyflute_ha_database \
  -i source/JHH_sequences.fasta \
  -m source/JHH_metadata.tsv \
  -o source/flusort_JHH_metadata.tsv
```

#### Required input for `flusort` 

  1. Multi FASTA Influenza Genomes in consensus sequence FASTA by segment derived from Nasal Swabs in the Johns Hopkins Hospital Network.
  
  3. Metadata `.tsv` file with the following metadata fields. **This file is manually curated**
     - sequence_ID (REQUIRED): JH#
     - sample_ID (REQUIRED): any continuous string without white spaces or tabs is accepted. 
     - run (REQUIRED): THe sequencing run ID - IV{year}Run{number} e.g. IV23Run6
     - date (REQUIRED): YYYY-MM-DD
     - passage_history: e.g. original
     - study_id: (OPTIONAL): study_tag
 
   - type: InfluenzaA or InfluenzaB 
   - subtype: H1N1, H3N2, Victoria
 
#### Output: 

A new metadata file with the following columns appended in **bold**

   - sequence_ID
   - sample_ID
   - run
   - date
   - passage_history
   - **type: InfluenzaA or InfluenzaB** (flusort)
   - **subtype: H1N1, H3N2, Victoria** (flusort) 

Flusort can also provide a plethura of summarized information now accessed by queries to [fludb](fludb). Details on additional functions of flusort can be viewed by running `fludb.py -h` and in the [README](scripts/flusort/README.md).

### 4. Upload all genome sequences and metadata to [fludb](seasonal-flu/sqlitedb/)
   
#### Initiate the database 

```
fludb/scripts/fludb_initiate.py
```

This will initiate the database in the home directory as `flu.db`. A convenient way to browse this database is by using the [sqlite-viewer vscode extension](https://marketplace.visualstudio.com/items?itemName=qwtel.sqlite-viewer). Just be sure to be lock the database from edits if browsing it extensively.


#### Upload JHH Sequences and Metadata

```
python fludb/scripts/upload_jhh.py \
   -db fldb.db \
   -f source/JHH_sequences.fasta
   -m source/flusort_JHH_metadta.fasta \
   --require-sequence
```

>[!IMPORTANT]
>The `--require-sequence` flag requires at least one genomic segment to be paired with a meatadata entry to be uploaded to `fludb.db`. If metadata information is availible in the metadata file without complementary sequencing data, it will be ignored.

### Upload Vaccine Virus genomes and metadata

```shell
python fludb/scripts/upload_jhh.py \
   -db fldb.db \
   -f source/JHH_sequences.fasta
   -m source/flusort_JHH_metadta.fasta \
   --require-sequence
```

### (OPTIONAL) Upload GISAID Sequences and metadata

>[!NOTE]
> This requires and un-edited `.xls` file from gisaid as metadata input and FASTA headers in the following (default) format: 
>  `Isolate name | Collection date | Passage details/history | Segment number | sample_id`

```shell
python fludb/scripts/upload_gisaid.py \
   -db fldb.db \
   -f source/GISAID_sequences.fasta
   -m source/GISAID_metadta.fasta \
```
### 5. Query sequences from 'fludb.db' 

Housing all sequences and their respective metadata allows for simplified and consistent formatting to query sequences, regardless of origin. A scaffold script for downloading sequences can be found here: [download.py](fludb/scripts/download.py). 

To download all segments by type and subtype into an appropriate directory structure for this pipeline, [simple script](scripts/fludb_download_seasonal_build_data.py) was written and can be executed by running the following from the seasonal-flu/ home directory.

```shell
python scripts/fludb_download_seasonal_build_data.py 
```

This will automatically populate the main directory with a directory called `data` and fill that directory with 3 sub directories called `h1n1`, `h3n2`, and `vic` each containing 8 segment-directories.  

## **Data Preparation Checkpoint**

You should have 2 major directories housing your data:
   - source/
   - data/ 

Below is what your datastructure sould look like. Regardless of what sequences are uploaded to fludb, the resulting data/ directory should be structured in the same way each and every time this pipeline is executed. 

### **source**: (2 files per "data source" e.g. GISAID or JHH)
```
source/
├── GISAID_metadata.xls - UNMODIFIED `.xls` file from GISAID. Do not convert to `csv`. 
├── GISAID_sequences.fasta
├── JHH_metadata.tsv
├── flusort_JHH_metadata.tsv - generated from [`flusort.py`](scripts/flusort/flusort.py)
├── JHH_sequences.fasta - UNMODIFIED 
├── vaccines.fasta - Manually Curated
└── vaccines.tsv - Manually Curate with column names identical to those in flusort_JHH_metadata.tsv

```

### **data/** (24 directories | 48 files) - generated from [`fludb_download_seasonal_build_data.py`](scripts/fludb_download_seasonal_build_data.py)

```
data
├── h1n1
│   ├── ha
│   │   ├── metadata.tsv
│   │   └── sequences.fasta
│   ├── mp
│   │   ├── metadata.tsv
│   │   └── sequences.fasta
│   ├── na
│   │   ├── metadata.tsv
│   │   └── sequences.fasta
│   ├── np
│   │   ├── metadata.tsv
│   │   └── sequences.fasta
│   ├── ns
│   │   ├── metadata.tsv
│   │   └── sequences.fasta
│   ├── pa
│   │   ├── metadata.tsv
│   │   └── sequences.fasta
│   ├── pb1
│   │   ├── metadata.tsv
│   │   └── sequences.fasta
│   └── pb2
│       ├── metadata.tsv
│       └── sequences.fasta
├── h3n2
   ├── {segment} - 1 folder per segment
      ├── metadata.tsv
      ├── sequences.fasta 
   ├── etc...
├── vic
│   ├── {segment}  - 1 folder per segment
│   │   ├── metadata.tsv
│   │   └── sequences.fasta
   ├── etc...  

```

## 5. Segment Builds (n=24)

Finally 😮‍💨 structured data 🎉🎉🎉! Below, a general description of how the [Snakefile](Snakefile) executes the construction of this pipline. After all desired data is properly formatted in the `data/`, the pipeline for all 24 builds can be executed by running:

```
snakemake --cores 8
```

>[!IMPORTANT]
> Replace cores with the number of desired cores.

### Build DAG Rulegraph Overview. 

Below is a simplified representation of the rules implemented for each build. Because wildcard constraints have been defined by subtype and segment, this general rulegraph is executed for h1n1, h3n2, and vic for all 8 segments. 

![DAG](rulegraph.png)

#### Breifly this pipeline performs the following for each segment of each build: 

1. Download and assign updated Clades with Nextclade

   > Automatically download updated nextclade dataset thus keeping all clade and subclade delineations up-to-date with each build execution. This is a not the way the nextstrain teams assigns clades and is (in my opinion) the most controversial step in this pipeline. [`augur clades'](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/clades.html). My reasoning is: nextclade can immediately provide an appendable table containing several [qc metrics](https://docs.nextstrain.org/projects/nextclade/en/stable/user/algorithm/06-quality-control.html) including missing data, sites, private mutations, clusters, frameshipts, stop codons etc, which we can later filter by [`augur filter`](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/filter.html) if needed. Furthermore, functions for glycosylation site prediction is included. In my opnion, these metrics should be considered at least qualitatively during filtering and later analysus. Thus, adding clades at this stage would reduce an additional `augur clades` step but store clade and subclade information in the metadata. Open to debating this.  

2. Append HA clade assignment to all segment metadata. 
3. Append quality metrics by segment 
4. Filter by coverage, qc status and length staus using [`augur filter`](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/filter.html)
```shell
"--query", "(coverage >= 0.9) & (`qc.overallStatus` == 'good')",  # Add qc_overallStatus == 'mediocre' if needed
"--min-length", str(min_length),
```
1.  Align 
2.  Build Raw Tree 
3.  Refine branches 
4.  Annotate 
5.  Infer ancestral sequences
6.  Translate sequences
7.  Export (auspice V2)
8.  Upload and deploy the builds to [Nextstrain](https://nextstrain.org/groups/PekoszLab)

# How to upload an auspice build to the group (example):

For detailed nextstrain group page settings and how to upload data, see the [Official Nextrain Documentation](https://docs.nextstrain.org/en/latest/guides/share/groups/index.html). 

## Login to nextstrain cli

```shell
nextstrain login
```
## Add a pathogen build

Replace `${YOUR_BUILD_NAME}` with the file name of the build. 

```shell
nextstrain remote upload \
    nextstrain.org/groups/PekoszLab/${YOUR_BUILD_NAME} \
    auspice/${YOUR_BUILD_NAME}.json
```
### Verify The Uploaded Build 

```shell
nextstrain remote list nextstrain.org/groups/PekoszLab
```
# Roadmap 

- [ ] Add t-SNE implementation for all builds using [pathogen-embed]()
   - Example implementations:
   - Manuscript: 
- [ ] Automated concatenated genome builds for h1n1 and h3n2
  - Proposed DAG 
    1.  [fludb](seasonal-flu/sqllitedb/) Query database for segment builds (24 total) including vaccine and previous season data for each subtype.
       - sequences.fasta 
       - metadata.fasta
       - A simple query such as `WHERE segment IN ('pb2', 'pb1', 'pa', 'ha', 'np', 'na', 'mp', 'ns')` should be sufficient.
    2.  Concatenate reference genomes
    3.  Concatenate reference annotation files (.gbk)
    4.  Append HA clade assignment to all segment metadata (left join from segment data)
    5.  Filter by length using `augur filter`
        - TODO: How can we simplify whole genome QC pre-concatenation? Add a segment length filter in fludb query? 
    6.  Index Genomes
    7.  Align
    8.  Raw Tree
    9.  Refine branches
    10. Annotate
    11. Infer ancestral sequences
    12. Translate sequences
    13. Export (auspice V2)

# History
- As of November 26, 2024, a Snakemake pipline for all 24 builds has been implemented to increase efficiency and reproducibility for all builds. 

# Acknowledgements
Automation by snakemake has increased our efficiency of these builds. The structure, scripts, and configuration filese herin are inspired tremendously by the [seasonal-flu](https://github.com/nextstrain/seasonal-flu) build maintained by the nextstrain team.