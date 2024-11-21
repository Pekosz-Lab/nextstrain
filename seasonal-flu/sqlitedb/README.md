# fludb

'fludb' is a consensus sequence database specifically designed to import, append, filter and export influenza genome consensus sequences. The motivation for this database is a 'two birds, one stone approach'.
- Firstly, the Pekosz Lab group required a standardized way to pass Influenza genomes generated in 'real time' into nextstrain and bi-weekly reports. 
- Secondly, we needed a way to filter, query, and format `.fasta` headers for gene-specific, concatentated genome, and reassortment analysis in our h1n1, h3n2 and influenza B pipelines.

fludb is not inteded to be a permenant data storage solution for influenza genomes, rather a lightweight tool for efficiently passing sequences and assicated metadata data for cleaning/filtering purposes. 

fludb is a crudely simple database with a single table at the moment built in [sqlite](https://www.sqlite.org/). There are many limitations with using a file-based RDBMS but they are outweighed by the advantages in our specific usecase as we do not host any fludb instance and thus user is required to generate their own.

# Getting Started with fludb

All dependecies for fluDB are included in the `seasonal-flu/environment.yml` file.

## 1. initiate the database

```shell
cd seasonal-flu/sqlitedb/scripts 

python fludb_initiate.py
```
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

|script|data schema|
|--|--|
|`fludb_jhh_upload.py`|Johns Hopkins Hospital|
|`fludb_ibv_jhh_upload.py`|Johns Hopkins Hospital|
|`fludb_gisaid_upload.py`|GISAID|

Users uploading Influenza A virus sequences (h1n1 and h3n2) should use the `fludb_jhh_upload.py` or `fludb_gisaid_upload.py` script. 

Influenza B virus sequences (vic) should use the `fludb_ibv_upload.py` script. The only difference here is that the pb2 and pb1 segments correlate with segment number 2 and 1, respecitvely due to the NCBI references used in consensus calling in the sequencing pipeline (described here: [10.1093/ofid/ofad577](https://academic.oup.com/ofid/article/10/12/ofad577/7424824?login=false)). This non-coniacle numbering is unique to the NCBI reference sequences.

The `fludb_gisaid_upload.py` script requires both an **UNMODIFIED** FASTA file and metadata.xls file from GISAID. The fasta file should containg the default (as of October 2024) header `Isolate name | Collection date | Passage details/history | Segment number | sample_id`.


## 4. Filtering and Querying `fludb_download.py` 

At minimum, `fludb_download.py` requires the following:

1. The specified `fludb.db` path (e.g. path/to/your/fludb.db)
2. The path and name of the resulting fasta file. This will be in standard fasta format.
3. The path and name of the resulting metadata file. This will be in .tsv format. 

NOTE: The metadata file will only have entries present in the fasta file.
NOTE: Queries to the database follow standard SQL language. 

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
