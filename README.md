# Pekosz Lab Nextstrain Builds

This repository houses all configuration data and **WORKING** scripts for the [Pekosz Lab nextstrain builds](https://nextstrain.org/groups/PekoszLab) as well as their required Nextclade datasets. Currently, 2 types of datasets are regularly maintained: 

1. 24 [Seasonal Influenza Genome Builds](seasonal-flu/) (H1N1, H3N2, and B/Vic) of circulaing viruses detected through the Johns Hopkins Hospital Network supported by [JH-CEIRR](https://www.ceirr-network.org/centers/jh-ceirr).

2. Specialized Builds Unique to Pekosz Lab-specific manuscripts.

> [!IMPORTANT]
> This repository is under construction thus scripts are not constructed for optimal run efficiency. See open github [Projects](https://github.com/Pekosz-Lab/nextstrain/projects?query=is%3Aopen) for ongoing efforts to optimize this pipeline. 

Current plan is to implement automation for the seasonal flu builds (24 for segment and 3 for concatenated genomes) using snakemake. I like the idea of using snakemake due to consistency between the nextstrain tool and our scale as opposed to nextflow but open to hearing other arguments.

# Pipeline

## Data Preparation

1. Influenza Genomes in consensus sequence FASTA by segment derived from Nasal Swabs in the Johns Hopkins Hospital Network.
2. ✅ Sorting consensus sequences of segments using [flusort](seasonal-flu/scripts/flusort) grouped by sequence ID. Creates a metadata table containing:  
   - type
   - subtype
   - genome_completeness
3. Append flusort metadata to isolate metadata (generated manually)
   - sequence_ID: JH#
   - sample_ID: Unformatted
   - run: IV{year}Run{number} e.g. IV23Run6
   - date: YYYY-MM-DD
   - passage_history: e.g. original
   - type: InfluenzaA
   - subtype: H3N2, H1N1, or Vic.
4. Upload clinical consensus sequences to [fludb](seasonal-flu/sqlitedb/)
   - OPTIONAL: upload Vaccine segment genomes
   - OPTIONAL: upload previous season genomes (representative or complete depending on dataset size)

## Segment Builds (n=24)

5. Query database for segment builds (24 total) including vaccine and previous season data for each subtype.
   - sequences.fasta 
   - metadata.fasta

    TODO: Merge IBV and IAV upload scripts 

6. Download and assign Clades with Nextclade

   > - TODO: Automatically download updated nextclade dataset thus keeping all clade and subclade delineations up-to-date with each build execution. This is a not the way the nextstrain teams assigns clades and is (in my opinion) the most controversial step in this pipeline. [`augur clades'](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/clades.html). My reasoning is: nextclade can immediately provide an appendable table containing several [qc metrics](https://docs.nextstrain.org/projects/nextclade/en/stable/user/algorithm/06-quality-control.html) including missing data, sites, private mutations, clusters, frameshipts, stop codons etc, which we can later filter by [`augur filter`](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/filter.html) if needed. Furthermore, functions for glycosylation site prediction is included. In my opnion, these metrics should be considered at least qualitatively during filtering and later analysus. Thus, adding clades at this stage would reduce an additional `augur clades` step but store clade and subclade information in the metadata. Open to debating this.  

7. Append HA clade assignment to all segment metadata 
8. Append quality metrics by segment 
9. Filter by coverage, qc status and length status using [`augur filter`](https://docs.nextstrain.org/projects/augur/en/stable/usage/cli/filter.html)

```shell
"--query", "(coverage >= 0.9) & (`qc.overallStatus` == 'good')",  # Add qc_overallStatus == 'mediocre' if needed
"--min-length", str(min_length),
```

10. Index Sequences
11. Align 
12. Build Raw Tree 
13. Refine branches 
14. Annotate 
15. Infer ancestral sequences
16. Translate sequences
17. Export (auspice V2)

## Concatenated Genome Builds

18. [fludb](seasonal-flu/sqllitedb/) Query database for segment builds (24 total) including vaccine and previous season data for each subtype.
   - sequences.fasta 
   - metadata.fasta
11. Concatenate reference genomes
12. Concatenate reference annotation files (.gbk)
13. Append HA clade assignment to all segment metadata (left join from segment data)
14. Filter by length using [`augur filter`]() 
    - TODO: How can we simplify whole genome QC pre-concatenation? Add a segment length filter in fludb query?
15. Index Genomes
16. Align 
17. Build Raw Tree 
18. Refine branches 
19. Annotate 
20. Infer ancestral sequences
21. Translate sequences
22. Export (auspice V2)

## How to upload an auspice build to the group (example): 

For detailed nextstrain group page settings and how to upload data, see the [Official Nextrain Documentation](https://docs.nextstrain.org/en/latest/guides/share/groups/index.html). 

### Login to nextstrain cli

```shell
nextstrain login
```

### Add a pathogen workflow 

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
