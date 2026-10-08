# Preparing the JHH input files (`source_prep/`)

> [!CAUTION]
> **Private data.** The run FASTAs, `run_dates.csv` and everything in
> `output/` are unpublished JHH patient-sample data. They stay on your computer
> and on the lab SharePoint. This folder's `.gitignore` keeps them out of git.
> Never upload, email or share them, and never use `git add -f`.

- Step by step: [Tutorial 2: Adding a New Sequencing Run](https://github.com/Pekosz-Lab/nextstrain/wiki/Tutorial-2-Adding-a-New-Sequencing-Run)
- Formats, messages and fixes: [Step 1: Source Data Preparation](https://github.com/Pekosz-Lab/nextstrain/wiki/Step-1-Source-Data-Preparation)

Quick reminder: put run FASTAs in `runs/` and `run_dates.csv` here, run
`python scripts/prepare_source.py`, and when it says `RESULT: READY` copy
`output/JHH_sequences.fasta` and `output/JHH_metadata.txt` into `source/`.
