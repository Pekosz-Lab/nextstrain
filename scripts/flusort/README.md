# flusort

## Description

Influenza segment annotation and cleaning script for Pekosz Lab Influenza Surveillance. The current release is targed towards maintainers of influenza genome sequences received from Dr. Heba Mostafa's team. `flusort` is comprised of 2 python scripts designed to perform BLAST searches on FASTA sequences and append subtype information to their headers based on the BLAST results. It also groups sequences based on their subtype and completeness, providing a summary of the input sequences.

`flusort` accepts multifasta files containing H1, H3 and IBV (tested on B/Victoria) segment sequences with a strict header following >XXXXXXX_Segment# example: `JH11111_1` which would be Sample JH11111 segment 1 (PB2). 

The resulting files included a fasta file with appended headers to identify the flu type and subtype with additional information which can be piped directly into [augur parse](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/parse.html) and [augur filter](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/filter.html). 

## Dependencies

1. flusort is written in python v3.X.X and requires [biopython](https://biopython.org/wiki/Download) (validated on v1.83) and [numpy](https://pypi.org/project/numpy/) (validated on v1.23.4).

2. BLAST+ Database: The current build of flusort requires BLAST 2.13.0+ CLI to be accesible via your global $PATH. Please [download](https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/) and test your local blast installation with `blastn -h` prior to running. By default, `pyflute.py` will search for the blastn databse in the "scripts" directory unless specified by the `-df` flag. The current BLAST database contains all Influenza A segments for H1N1 and H3N2 as well as IBV Segments for B/Victoria. 

```
pip install biopython numpy
```

## Arguments

Perform BLAST searches on FASTA sequences.

arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input_file INPUT_FILE
                        Path to the input FASTA file.
  -db BLAST_DB, --blast_db BLAST_DB
                        Path to the custom BLAST database file.
  -m METADATA, --metadata METADATA
                        Path to the metadata file (CSV or TSV).
  -f OUT_ORIGINAL_FASTA, --out_original_fasta OUT_ORIGINAL_FASTA
                        Path to save the original FASTA file with subtype info.
  -o OUT_FLUDB, --out_fludb OUT_FLUDB
                        Path to save the fludb metadata results.
  --out_grouped [OUT_GROUPED]
                        Path to save the grouped results. Optional.
  --out_subtype_fasta [OUT_SUBTYPE_FASTA]
                        Path to save the FASTA file with subtype information. Optional.
  --out_BLAST_no_hits [OUT_BLAST_NO_HITS]
                        Path to save sequences which did NOT RETURN BLAST hits. Optional.
  -O OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Directory to save BLAST+ output file (if specified). Optional.

## Example Usage

```
python flusort.py \
  -db database_path/database_name
  -i input_sequences.fasta \
  -m input_metadata.tsv \
  -f output_sequences.fasta \
  -o output_appended_metadata.tsv
```

Initial metadata table


Final metadata table with type and subtype appended: 




# Changelog 


## 2024-06-26

- Depreciated flusory_split.py.
- Specification of header metadata delimiters.
- Appended headers now compatible with [`augur parse`](): 
  - sequence_id_segment_number
  - sequence_id
  - segment_number
  - virus_type_suffix
  - subtype
  - completeness

# Feature Roadmap 


