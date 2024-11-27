# Pekosz Lab Nextclade Datasets

This repository houses [nextclade](https://github.com/seasonal-flu/nextclade/tree/master) datasets used in the Pekosz Lab Nextstrain builds. 

## Notes

For Influenza A builds, datasets regularly maintained by the [nextstrain](https://nextstrain.org/)team: (https://github.com/nextstrain/nextclade_data/tree/release/data/nextstrain) are pulled into this repository.

For Influenza B builds, all datasets have been created according to specifications found in the [dataset curation guidelines](https://github.com/nextstrain/nextclade_data/blob/release/docs/dataset-curation-guide.md) for [Nexclade CLI](https://docs.nextstrain.org/projects/nextclade/en/stable/user/nextclade-cli/index.html) v3 compatability.

### Custom Influenza B Datasets

|Virus|Segment|Reference cds Accession|Date Updated|
|---|---|---|---|
|Influenza B|[pb2](flu/vic/pb2/)|[KC866604.1](https://www.ncbi.nlm.nih.gov/nuccore/KC866604.1/)|2024-04-29|
|Influenza B|[pb1](flu/vic/pb1/)|[KC866603.1](https://www.ncbi.nlm.nih.gov/nuccore/KC866603.1)|2024-04-29|
|Influenza B|[pa](flu/vic/pa/)|[KC866602.1](https://www.ncbi.nlm.nih.gov/nuccore/KC866602.1)|2024-04-29|
|Influenza B|[np](flu/vic/np/)|[KC866605.1](https://www.ncbi.nlm.nih.gov/nuccore/KC866605.1)|2024-04-29|
|Influenza B|[mp](flu/vic/mp/)|[CY115152.1](https://www.ncbi.nlm.nih.gov/nuccore/CY115152.1/)|2024-04-29|
|Influenza B|[ns](flu/vic/ns/)|[KC866606.1](https://www.ncbi.nlm.nih.gov/nuccore/KC866606.1)|2024-04-29|
|Influenza B|[na](flu/vic/na/)|[CY073894.1](https://www.ncbi.nlm.nih.gov/nuccore/CY073894.1)|2024-05-23|

## Each dataset contains the following files: 
- Reference `reference.fasta`
- reference annotation `genome_annotation.gff`
- annotation genbank `genome_annotation.gb`
- `README.md`
- `changelog.md`

## Changelog

- 2024-07-16: Influenza A datasets created and deposited.
- 2024-05-23: NA Segment added to include the NB cds from [CY073894.1](https://www.ncbi.nlm.nih.gov/nuccore/CY073894.1).
- 2024-04-29: Repo created, Influenza B Victoria non HANA segments updated.
