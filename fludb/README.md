# fludb

`fludb` is a consensus sequence database specifically designed to import, append, filter and export influenza genome consensus sequences. The motivation for this database is a 'two birds, one stone approach'.

- Firstly, the Pekosz Lab group required a standardized way to pass Influenza genomes generated in 'real time' into nextstrain and bi-weekly reports. 
- Secondly, we needed a way to filter, query, and format `.fasta` headers for gene-specific, concatentated genome, and reassortment analysis in our h1n1, h3n2 and influenza B pipelines.

fludb is not inteded to be a permenant data storage solution for influenza genomes, rather a lightweight tool for efficiently passing sequences and assicated metadata data for cleaning/filtering purposes. 

fludb is a crudely simple database with a single table at the moment built in [sqlite](https://www.sqlite.org/). There are many limitations with using a file-based RDBMS but they are outweighed by the advantages in our specific usecase as we do not host any fludb instance and thus user is required to generate their own.

# fludb Quickstart

## Initiate a local instance of your database.

```shell
python fludb_initiate.py
```

## Upload your data

```shell
python seasonal-flu/fludb/scripts/upload_jhh.py \
    -d fludb.db \
    -f data/JHH_sequences.fasta \
    -m data/JHH_metadata.tsv \
    --require-sequence
```  

## Query and download your data

### Download only Influenza B Victoria NS segments with a hNEC1 Siat 2 passage history
```shell
python fludb_download.py \
    -d fludb.db \
    -f sequences.fasta \
    -m metadata.tsv \
    --headers sample_id \
    --filters "subtype='vic',passage_history='hNEC1S2'" \
    --segments ns
```

### Download complete

# fludb Detailed Start Guide

All dependecies for fluDB are included in  `seasonal-flu/environment.yml`.

## 1. initiate the database

```shell
python fludb_initiate.py
```

- sequence_ID (KEY): 
- sample_ID:
- type: 
- subtype:
- date:
- passage_history:
- study_id:
- sequencing_run:
- location:
- database_origin:
- pb2: sequence
- pb1: sequence
- pa: sequence
- ha: sequence
- np: sequence
- na: sequence
- mp: sequence
- ns: sequence

## 2. Preparing your data
 
Uploading data requires 2 files in the following formats.

1. A `.fasta` file containing header information in the following format `seqid_segment number` (e.g. JH12345_1). The databse utilizes the seqid (JH number) as the relational key. Additional information in the header is not compatible with the provided upload scripts and will need to be adapted to fit your specific headers. 

2. A metadata table with the following columns:
   - **seqid**: must have a matching sequences in the `.fasta` file.
   - **sample_id**: an additional identifier such as sample ID or name. 
   - **subtype**: must be h1n1, h3n2, or vic
   - **collection_date**: in YYYY-MM-DD format
   - **passage_history**: The passage history of the sequence. 
   - **study_id**: This is intended to be used as a shortcut alias for easier querying across experiments. 

## 3. Uploading your data

Once initialized, you'll notice there are several scripts for uploading influenza genome and metadata to the database depending on the source of your data.

|script|originating data|required input|
|--|--|--|
|`upload_jhh.py`|Johns Hopkins Hospital|`sequences.fasta` `metadata.tsv`|
|`upload_gisaid.py`|GISAID|`sequences.fasta`, `metadata.tsv`|

### `upload_jhh.py`

- **Sequences in FASTA format**
  - Headers must follow standard JH# sequencing identifiers of any length (e.g. JH1234 or JH11111)
- **metadata.tsv**
  - sequencing_ID
  - sample_ID
  - sequencing_run
  - date: Must be in YYYY-MM-DD format. Unknown month or days are accepted (e.g. 2024-01-XX or 2023-XX-XX).
  - passage_history
  - type
  - subtype

#### example
```shell
python seasonal-flu/fludb/scripts/upload_jhh.py \
    -d fludb.db \
    -f data/JHH_sequences.fasta \
    -m data/JHH_metadata.tsv \
    --require-sequence
```  

### `fludb_gisaid_upload.py`

The `gisaid_upload.py` script requires both an **UNMODIFIED** FASTA file and metadata.xls file from GISAID. The fasta file should containg the default (as of October 2024) header formay: `Isolate name | Collection date | Passage details/history | Segment number | sample_id`.

#### example usage

```shell
python seasonal-flu/fludb/scripts/upload_gisaid.py \
    -d fludb.db \
    -f source/20241021_GISAID_Epiflu_Sequence.fasta \
    -m source/20241021_GISAID_isolates.xls
```

## 4. Querying Sequences `fludb_download.py` 

The download script will produce 2 files.
  1. sequences.fata
  2. metadata.tsv

### At minimum, `fludb_download.py` requires the following:

- A Database connection`fludb.db` path (e.g. path/to/your/fludb.db)
- The path and name of the resulting fasta file. This will be in standard fasta format.
- The path and name of the resulting metadata file. This will be in .tsv format. 

>[!NOTE] 
> - The metadata file will only have entries present in the fasta file.
> - Queries to the database follow standard SQL language. 

fludb_download.py [-h] -d DB -f FASTA -m METADATA [--headers [{seq_id,sample_id,subtype,collection_date,passage_history,study_id,segment,sequencing_run} ...]] [--filters [FILTERS ...]]
                         [--segments [{pb2,pb1,pa,ha,np,na,mp,ns} ...]]

### Usage

**-h, --help**

> show this help message and exit

**-d DB, --db DB**

> Path to the SQLite database file.

**-f FASTA, --fasta** 

> FASTA Path to the output FASTA file.

**-m METADATA, --metadata** 

> METADATA Path to the output metadata TSV file.

**--headers**

> OPTIONS: seq_id,sample_id,subtype,collection_date,passage_history,study_id,segment,sequencing_run

> Metadata fields to include in the FASTA header.

**--filters [FILTERS ...]**

> SQL conditions for querying the database are accepted. 

> Use AND, OR, and NOT for complex queries. Passage History Example: "passage_history='hNEC1S2'", Date range example: "collection_date BETWEEN '2024-01-01' AND '2024-12-31'"

**--segments OPTIONS: pb2,pb1,pa,ha,np,na,mp,ns**
    
> Specific segments to include in the FASTA file. 

> Example: ha pb1 

### Example Queries

Example to download only ibv NS sequences from working stocks: 

```shell
python fludb_download.py \
    -d fludb.db \
    -f sequences.fasta \
    -m metadata.tsv \
    --headers sample_id \
    --filters "subtype='vic',passage_history='hNEC1S2'" \
    --segments ns
```

#### References

FluDB is partially inspired by [fauna](https://github.com/nextstrain/fauna).

#### Feature roadmap 

- [ ] Add genome-completeness column automatically refreshed with each upload.
