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

### `flusort.py`

- -i,  --input_file: Path to the input FASTA file. (Required)
- -db,  --blast_db: Path to the custom BLAST database file. (Optional)
- -o,  --output_directory: Path to the output directory. Defaults to 'flusort_out' in the script's directory. (Optional)

#### Output

- output.fasta: Filtered sequences written to a single file if not split.
- segment_{segment_number}_sorted.fasta: Filtered sequences for each segment written to separate files if the split flag is used (-s, --split).

## Example Usage

first running `flusort.py`

```
python flusort.py -i ./example_input/flusort_example.fasta
```
All outputfiles will be  directory named `flusort_output` will be created unless specified.

# Changelog 

## 2024-06-26
- Depreciated flusory_split.py.
- Specification of header metadata delimiters.
- Appended headers now compatible with `augur parse`: 
  - sequence_id_segment_number
  - sequence_id
  - segment_number
  - virus_type_suffix
  - subtype
  - completeness



# Feature Roadmap 

## Reassortment Data Cleaning
A `balance.py` script which leverages not only the presence of complete genomes, but coverage and fasta quality to clean datasets appropriate for concatenated genome and reassortment analysis.

