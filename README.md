# Pekosz Lab Seasonal Influenza Nextstrain Builds 🦠 

This repository houses all scripts, snakefiles, and configuration files for the [Pekosz Lab nextstrain builds](https://nextstrain.org/groups/PekoszLab) 

Currently, 24 total builds are maintained for all 8 segments of circulaing H1N1, H3N2, and B/Vic viruses detected through the Johns Hopkins Hospital (JHH) Network supported by [JH-CEIRR](https://www.ceirr-network.org/centers/jh-ceirr). As of [2024-11-26](#history), all builds are constructed using a simplified [snakemake](https://snakemake.readthedocs.io/en/stable/) pipline.

# Quickstart: Getting Started with the 24 segment build for H1N1, H3N2 and B/Victoria

>[!WARNING]
>For this tutorial, all scripts must be run from the `nextstrain/` home directory. 

**NOTE:** If you already have a `fludb.db` database build, you can skip ahead to [Step 5](## 5. Query genomes and metadata and depost in the `data/` directory using [download.py](fludb/scripts/download.py)

## 1. Clone this repository setup and activate your environment. 

>[!NOTE]
> Dependencies for this build are maintained through `conda`. Download the latest version [here](https://anaconda.org/anaconda/conda). A breif introduction to conda and conda environments can be found [here](https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html).

- Clone: `git clone https://github.com/Pekosz-Lab/nextstrain.git`

- Navigate to the head directory `cd nextstrain` 

- Build the environment and base dependencies `conda env create -f environment.yml`

- Activate the environment `conda activate pekosz-nextstrain`

## 2. Access genome and metadata from JHH and GISAID (vaccine strains) and place in a directory called `source/`

- Create the `source`, `data` and `results` directories within the `nextstrain/` directory. 

```
mkdir source data results
```

- Populate the `source/` folder with the following files:

1. JHH_sequences.fasta
2. JHH_metadata.tsv
3. vaccines.fasta

The `source/` folder with all build data can be accessed [here](https://livejohnshopkins.sharepoint.com/:f:/r/sites/pekoszlab/Shared%20Documents/%5B02%5D%20Virus-Specific-Data/Seasonal-Influenza/%5B01%5D%20-%20Seasonal_Directories/2023-24_Pekosz_Lab_Influenza/01_mostafa_clinical_sequences/EA20241217_nextstrain/source?csf=1&web=1&e=gl9dV9). 

Download the all data in the `source/` folder or overwrite your source folder and moving it to the repo head directory `nextstrain/`. You `nextstrain` directory will now have the following additional folders: 

```
nextstrain/
├── source/
   ├── GISAID_metadata.xls
   ├── GISAID_sequences.fasta
   ├── JHH_metadata.tsv
   ├── JHH_sequences.fasta
   ├── vaccines.fasta
   └── vaccines.tsv
├── data/ # This will be empty 
├── results/ # This will be empty
```

>[!WARNING]
> These builds are designed to ingest influenza genome data and metadata originating from [GISAID](https://gisaid.org/) and internally from the Mostafa lab at the Johns Hopkins Hospital (eJHH) network. Due to the [regulated access](https://gisaid.org/terms-of-use/) to all GISAID data, individual crdentials are needed to access these data and cannot be shared publicly. Furthermore, Influenza Genomes from the JHH network accessed ahead of publishing to GISAID are private and cannot be shared publically in this repository.


## 3. Append type and subtype data to its respective `metadata.tsv`using [flusort](scripts/flusort)

```shell
python scripts/flusort/flusort.py \
  -db scripts/flusort/blast_database/pyflute_ha_database \
  -i source/JHH_sequences.fasta \
  -m source/JHH_metadata.txt \
  -f source/flusort_JHH_sequences.fasta \
  -o source/flusort_JHH_metadata.tsv
```

`flusort.py` requires the following 2 input files:

  1. `JHH_sequences.fasta`: A FASTA file containing influenza genomes by segment in JHH format: 
   - e.g. JH121234_4
      - JH121234 = sample_ID
      - _4 = segment 4 (HA)
   
  3. `JHH_metadata.tsv`: A metadata file with the following fields: **WARNING: This file is manually curated**
     - `sequence_ID` (REQUIRED): JH# 
     - `sample_ID` (REQUIRED): JH# For the seasonal influenza builds, the sample_ID is identical to the sequence ID.
     - `run` (REQUIRED): The sequencing run ID - IV{year}Run{number} e.g. IV23Run6
     - `date` (REQUIRED): YYYY-MM-DD
     - `passage_history`: e.g. original
     - `study_id`: (OPTIONAL): study_tag

Flusort will append the `JHH_metadata.tsv` with 2 columns specifying the type and subtype in bold below:

>[!NOTE]
> The `sample_ID` column is used as the value for all `--metadata-id-columns` augur functions when appropriate. 

   - **type: InfluenzaA or InfluenzaB** (flusort)
   - **subtype: H1N1, H3N2, Victoria** (flusort) 

## 4. Upload all genome and metadata to [`fludb`](fludb/)

- Initiate the database: 

```shell
python fludb/scripts/fludb_initiate.py
```

- Upload JHH sequences [upload_JHH.py](fludb/scripts/upload_jhh.py)

```shell
python fludb/scripts/upload_jhh.py \
    -d fludb.db \
    -f source/flusort_JHH_sequences.fasta \
    -m source/flusort_JHH_metadata.tsv \
    --require-sequence
```  

>[!IMPORTANT]
>The `--require-sequence` flag for [upload_JHH.py](fludb/scripts/upload_jhh.py) requires at least one genomic segment to be paired with a metadata entry to be uploaded to `fludb.db`. 
>If JHxx entry is present in the metadata without complementary sequencing data in the FASTA file, it will be ignored.

- Upload Vaccine Strain [upload_vaccine.py]()

```shell
python fludb/scripts/upload_vaccine.py \
  -d fludb.db \
  -f source/vaccine.fasta
```

- (**OPTIONAL**) Upload GISAID reference data to fludb [upload_gisaid.py](fludb/scripts/upload_gisaid.py) 

```shell
python fludb/scripts/upload_gisaid.py \
    -d fludb.db \
    -f source/20241021_GISAID_Epiflu_Sequence.fasta \
    -m source/20241021_GISAID_isolates.xls
```

>[!WARNING]
> This requires 2 files: 1) an **UNMODIFIED** `.xls` file from GISAID as metadata input. 2) A FASTA file with headers in the following (default) format: 
>  `Isolate name | Collection date | Passage details/history | Segment number | Isolate ID`


## 5. Query genomes and metadata and depost in the `data/` directory using [download.py](fludb/scripts/download.py)

The [fludb_download_seasonal_build_data.py](scripts/fludb_download_seasonal_build.py) script will populate the `data/` with subtype build folders called `h1n1`, `h3n2`, and `vic`. 

- Each subtype build folder will contain 8 segment folders: `pb2`, `pb1`, `pa`, `ha`, `np`, `na`, `mp`, `ns`.

- Each segment will contain the following files:
   - sequences.fasta
   - metadata.tsv 

```shell
python scripts/fludb_download_seasonal_build.py
```

## CHECKPOINT 

Below is what your data structure sould look like. Regardless of what sequences are uploaded to fludb, the resulting data/ directory should be structured in the same way each and every time this pipeline is executed.

```
nextstrain/
│   source/
│   ├── GISAID_metadata.xls - UNMODIFIED `.xls` file from GISAID. Do not convert to `csv`. 
│   ├── GISAID_sequences.fasta
│   ├── JHH_metadata.tsv
│   ├── flusort_JHH_metadata.tsv - generated from [`flusort.py`](scripts/flusort/flusort.py)
│   ├── JHH_sequences.fasta - UNMODIFIED 
│   ├── vaccines.fasta - Manually Curated
│   └── vaccines.tsv - Manually Curate with column names identical to those in flusort_JHH_metadata.tsv
├── data/
│   ├── h1n1
│   │   ├── ha
│   │   │   ├── metadata.tsv
│   │   │   └── sequences.fasta
│   │   ├── mp
│   │   │   ├── metadata.tsv
│   │   │   └── sequences.fasta
│   │   ├── na
│   │   │   ├── metadata.tsv
│   │   │   └── sequences.fasta
│   │   ├── np
│   │   │   ├── metadata.tsv
│   │   │   └── sequences.fasta
│   │   ├── ns
│   │   │   ├── metadata.tsv
│   │   │   └── sequences.fasta
│   │   ├── pa
│   │   │   ├── metadata.tsv
│   │   │   └── sequences.fasta
│   │   ├── pb1
│   │   │   ├── metadata.tsv
│   │   │   └── sequences.fasta
│   │   └── pb2
│   │       ├── metadata.tsv
│   │       └── sequences.fasta
│   ├── h3n2
│      ├── {segment} - 1 folder per segment
│      │   ├── metadata.tsv
│      │   ├── sequences.fasta 
│      ├── etc...
│   ├── vic
│   │  ├── {segment}  - 1 folder per segment
│   │  │   ├── metadata.tsv
│   │  │   └── sequences.fasta
│      ├── etc...  
├── results

```

## 6. Execute Snakemake build 

From the `nextstrain/` directory execute the following to initiate the build. 

```
snakemake --cores 8
```

## 7. Upload the builds to nextstrain

### Uploading a single build `.json` 

Replace `${YOUR_BUILD_NAME}` with the file name of the build. 

```shell
nextstrain remote upload \
    nextstrain.org/groups/PekoszLab/${YOUR_BUILD_NAME} \
    auspice/${YOUR_BUILD_NAME}.json
```

#### Verify The Uploaded Build 

```shell
nextstrain remote list nextstrain.org/groups/PekoszLab
```

# Roadmap 

- [ ] Add t-SNE implementation for all builds using [pathogen-embed](https://pypi.org/project/pathogen-embed/)
   - Manuscript: https://bedford.io/papers/nanduri-cartography/
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


# Build DAG Rulegraph Overview. 

Below is a simplified representation of the rules implemented for each build. Because wildcard constraints have been defined by subtype and segment, this general rulegraph is executed for h1n1, h3n2, and vic for all 8 segments. 

![DAG](rulegraph.png)

## Breifly this pipeline performs the following for each segment of each build: 

1. Download and assign updated Clades with Nextclade

   - Automatically download updated nextclade dataset thus keeping all clade and subclade delineations up-to-date with each build execution. This is a not the way the nextstrain teams assigns clades and is (in my opinion) the most controversial step in this pipeline (see [augur clades](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/clades.html)) My reasoning is: nextclade can immediately provide an appendable table containing several [qc metrics](https://docs.nextstrain.org/projects/nextclade/en/stable/user/algorithm/06-quality-control.html) including missing data, sites, private mutations, clusters, frameshipts, stop codons etc, which we can later filter by [`augur filter`](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/filter.html) if needed and is metadata-centered. Furthermore, a function for glycosylation site prediction is included. In my opnion, these metrics should be considered at least qualitatively during filtering and later analysus. Thus, adding clades at this stage would reduce an additional `augur clades` step but store clade and subclade information in the metadata. Open to debating this.  

2. Append HA clade assignment to all segment metadata.
3. Append quality metrics by segment
4. Filter by coverage, qc status and length staus using [`augur filter`](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/filter.html)

```shell
"--query", "(coverage >= 0.9) & (`qc.overallStatus` == 'good')",  # Add qc_overallStatus == 'mediocre' if needed
"--min-length", str(min_length),
```

5.  Align 
6.  Build Raw Tree 
7.  Refine branches 
8.  Annotate 
9.  Infer ancestral sequences
10. Translate sequences
11. Export (auspice V2)
12. Upload and deploy the builds to [Nextstrain](https://nextstrain.org/groups/PekoszLab)

# How to upload an auspice build to the group (example):

For detailed nextstrain group page settings and how to upload data, see the [Official Nextrain Documentation](https://docs.nextstrain.org/en/latest/guides/share/groups/index.html). 

## Login to nextstrain cli

```shell
nextstrain login
```
## Uploading all 24 pathogen builds constructed in this pipline to

### Private Deployment 

a custom script has been make to deploy all 24 builds simultaneously 
- [scripts/nextstrain_upload_private.py](scripts/nextstrain_upload_private.py)
```
python scripts/nextstrain_upload_private.py
```

# History
- As of November 26, 2024, a Snakemake pipline for all 24 builds has been implemented to increase efficiency and reproducibility for all builds. 

# Acknowledgements
Automation by snakemake has increased our efficiency of these builds. The structure, scripts, and configuration filese herin are inspired tremendously by the [seasonal-flu](https://github.com/nextstrain/seasonal-flu) build maintained by the nextstrain team.