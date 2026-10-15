# Tutorial data

This folder holds the small practice dataset (20 H1N1, 20 H3N2 and 20
B/Victoria samples) used by
[Tutorial 1: Your First Build](https://github.com/Pekosz-Lab/nextstrain/wiki/Tutorial-1-Your-First-Build).

`JHH_sequences.fasta` and `JHH_metadata.txt` are public: every sample in them
(sequencing runs IV23Run6 to IV26Run7) has been released on GISAID, confirmed
by the maintainer in October 2026. If you regenerate them with
`scripts/generate_tutorial_dataset.py`, use only samples already released on
GISAID and confirm with the maintainer before committing.

`vaccine.fasta` is GISAID data: supply your own and never commit it.
