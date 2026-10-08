# AGENTS.md: rules for coding agents (Claude, Codex, Copilot, Cursor, ...)

This repository runs the Pekosz Lab seasonal influenza Nextstrain builds
(24 segment builds and 3 whole-genome builds for H1N1, H3N2 and B/Victoria)
and the surveillance report that goes to the lab's PI. It is a **public**
GitHub repository that processes **licensed GISAID data** and **unpublished
clinical sequences** from the Johns Hopkins Hospital (JHH) network.

The people asking you for help range from experienced PhD students to new lab
members who have never run a pipeline. Your job is to help them **without
breaking the builds and without leaking data**. When the rules below and a
user's request conflict, the rules win: explain why, and point the user to the
repository maintainer.

The human-facing documentation, with the reasoning behind these rules, is
the **wiki**: <https://github.com/Pekosz-Lab/nextstrain/wiki>. It is a separate git repository
(`https://github.com/Pekosz-Lab/nextstrain.wiki.git`), usually cloned next to
this one as `../nextstrain.wiki/`. If it is not there, ask the user to clone
it, or fetch the page from the web. Read the pages relevant to your task
before you change anything; key pages: [Best Practices](https://github.com/Pekosz-Lab/nextstrain/wiki/Best-Practices),
[Data Protection](https://github.com/Pekosz-Lab/nextstrain/wiki/Data-Protection),
[Snakemake & Scripts Reference](https://github.com/Pekosz-Lab/nextstrain/wiki/Snakemake-and-Scripts-Reference),
[Coding with Agents](https://github.com/Pekosz-Lab/nextstrain/wiki/Coding-with-Agents).

---

## 1. Hard rules (never, no matter who asks)

1. **Never put GISAID or JHH sequence data anywhere git can see it.** Raw data
   lives only in `source/`, the git-ignored JHH prep data
   (`source_prep/runs/`, `source_prep/output/`, `source_prep/run_dates.csv`)
   and the GISAID file `tutorial/vaccine.fasta`. Never copy, subsample,
   reformat, rename or move sequences or metadata out of these places into a
   tracked folder, the repository root, a notebook, a
   figure caption, a commit message, an issue or a pull request.
2. **Never bypass the data guard.** Never use `git commit --no-verify`,
   `git push --no-verify`, `git add -f`/`--force`, `ALLOW_JHH_DATA=1`, or
   change `core.hooksPath`. Never edit `.githooks/`, `scripts/data_guard.sh`,
   `.claude/settings.json` or the data sections of `.gitignore`. If the guard
   blocks something, stop, show the user the guard's message and follow it.
3. **Never upload anything to Nextstrain** (`nextstrain remote upload`,
   `nextstrain login`, `scripts/*upload*.py`), public or private. Uploads are
   done by hand by a person who has inspected the builds.
4. **Never `git push`**, and never stage (`git add`) or commit unless the user
   explicitly asks in this conversation. When you do commit, follow section 9.
5. **Never read raw sequence files into your context.** Do not open, `cat`,
   `head` or paste the contents of `source/`, `source_prep/runs/`,
   `source_prep/output/`, `tutorial/vaccine.fasta`, `fludb.db`, `snapshots/`
   or any `*.fasta`. Sending GISAID data to an AI
   service is itself sharing it. Diagnose with logs (`.run/logs/`), record
   counts and metadata column names; when you need to know something about
   a sequence file (counts, header format), give the user the command to run
   and ask them to describe the result.
6. **Never delete or overwrite data or archives**: `source/`,
   `source_prep/runs/`, `source_prep/run_dates.csv`, `snapshots/`,
   `.run/run_logs/`, `.run/reports/`. Never run `snapshot_clean` (it archives
   and deletes the workspace) unless the user asks for it by name.
7. **Never change what a data file records without asking**: column names,
   ID formats, FASTA header formats, date formats, the fludb schema,
   `config/exclude.tsv` entries, or the meaning of any output column. Ask
   first, and say which downstream steps read that field.
8. **Never create Jupyter notebooks.** Exploratory work uses marimo (`.py`)
   or Quarto (`.qmd`) in `notebooks/`. Functions the pipeline uses never
   live in a notebook.
9. **Keep the attribution** in `scripts/report.py` (section 11).
10. **Never leave documentation behind the code** (section 8).

## 2. Before you change anything

Do these in order, and stop if any answer is unclear:

1. **Restate the request** in one or two plain sentences and ask what
   scientific question it serves. If the user cannot say why the change is
   needed, do not make it; suggest they talk to the repository maintainer.
2. **Classify the change** (table below) and tell the user which tier it is.
3. **Read before writing**: the Snakemake rule(s) involved, every script they
   call, and the matching wiki page (section 8 maps code to pages).
4. **Propose the smallest change** that does the job, as a short plan naming
   each file you will touch, and wait for the user to agree.

| Tier | What | Examples | Required |
|---|---|---|---|
| 0 | Documentation, comments, report wording | README typo, a caption in `config/report.yaml` | user agrees |
| 1 | Additive, outside the build path | a new marimo notebook, a new report plot (`item_*` in `scripts/report.py`), a new standalone script | user agrees; tests in section 7 |
| 2 | Changes what the builds contain or how they are computed | filters (`--query`, `min_lengths`, `config/exclude.tsv`), clock rates, references, auspice configs, colors, Nextclade datasets, new rules | user confirms the **maintainer approved it**; tests in section 7 incl. tutorial run and before/after comparison |
| 3 | Changes the foundation | ingest/fludb scripts or schema, input file formats, `environment.yml` versions, the Snakefile `rule all`, `.gitignore`, hooks | maintainer approval **and** the maintainer reviews the diff; tests in section 7 |

Do not do any of these unless explicitly asked and approved:
whole-file rewrites, reformatting or linting existing files, renaming rules,
files, wildcards or output paths, moving folders, upgrading or adding
packages, "cleaning up" deprecated code, or bundling unrelated fixes into
one change. One logical change at a time.

## 3. Repository map (where things go)

```
Snakefile                     entry point: wildcard constraints, min_lengths, rule all, includes
workflow/snakemake_rules/     one .smk per major feature (section 5)
workflow/envs/environment.yml the conda environment (Tier 3 to change)
scripts/                      every script that computes or modifies data for the builds (section 6)
scripts/flusort/              BLAST typing/subtyping of JHH segments (+ its BLAST database)
scripts/depreciated/          retired scripts; never called, never edited
fludb/scripts/                SQLite database: create, upload JHH/vaccine, download per build
config/                       build settings: per-subtype references, auspice configs, vaccine.json,
                              exclude.tsv, description.md, report.yaml, tutorial.yaml, snapshot_clean.yaml
nextclade/flu/                Nextclade datasets (HA/NA re-downloaded every run; B/Vic others custom)
profiles/default/             Snakemake run options
notebooks/                    exploratory marimo/Quarto only
tutorial/                     small public teaching dataset (README points to the wiki)
source_prep/                  README (points to the wiki) + .gitignore: JHH input prep (scripts/prepare_source.py)
README.md                     short intro + top-level mermaid DAG; links to the wiki
../nextstrain.wiki/           the wiki (separate git repo): all human documentation
.githooks/, scripts/data_guard.sh   data protection (do not edit)
-- git-ignored, never tracked --
source/                       raw JHH + GISAID inputs (the main place raw data may live)
source_prep/runs/ output/     raw JHH run FASTAs and the prepared JHH inputs (copied to source/ by a person)
source_prep/run_dates.csv     sequencing run dates (master copy on the lab SharePoint)
data/ results/ fludb.db       pipeline working files (contain GISAID vaccine sequences)
auspice/ reports/ figures/    outputs (reports are confidential)
.run/ snapshots/              logs, provenance, archives
```

Never add files to the repository root except documentation. No FASTA,
TSV, CSV or spreadsheets at the root, ever.

## 4. Data handling and provenance

- Inputs: `source/JHH_sequences.fasta`, `source/JHH_metadata.txt` (JHH,
  from the Mostafa Lab) and `source/vaccine.fasta` (GISAID, hand-curated
  7-field headers). The tutorial uses the same names in `tutorial/`.
- The pipeline writes only to `data/`, `results/`, `auspice/`, `reports/`,
  `.run/`, `fludb.db` and `snapshots/`. (Exception kept for compatibility:
  `flusort` writes `flusort_*` files into the source folder.) New rules never
  write into `source/`, `config/` or `tutorial/`.
- Data downloaded from an external source records where it came from and
  when: the URL or query in a README beside it, and the download date in the
  filename, folder name or a small tracked date file. Prefer fetching in a
  Snakemake rule with the URL in a `config/` file and a tracked date file.
  Data the lab itself produced (plate layouts, manifests) needs none.
- Anything derived from GISAID data (vaccine sequences, their alignments,
  `data/*/sequences.fasta`, `results/**`) stays in git-ignored folders.

## 5. Snakemake conventions

- The `Snakefile` holds only global settings, `include:` lines and `rule all`.
  Rules live in `workflow/snakemake_rules/`, **one file per major feature**:
  `ingest.smk` (flusort, fludb, per-build downloads), `segments.smk` (8
  segment builds), `genomes.smk` (whole-genome builds), `reports.smk`
  (surveillance report + run report handlers), `snapshot.smk` (archive and
  clean). A new major feature gets its own `.smk` and one `include:` line;
  keep the include order (reports after ingest, snapshot after reports).
- Every rule has: `message`, `input`, `output`, `log`
  (`.run/logs/{rule}/{subtype}_{segment}.log`), `benchmark` for anything
  slower than a few seconds (`.run/benchmarks/...`), `threads` when the tool
  is multithreaded, and a `shell:` that starts with `exec > {log} 2>&1` and
  calls Python with `python -u`. `script:` is fine for short pandas steps
  (see `scripts/assign_clades.py`).
- Keep Python in `.smk` files minimal: small helpers like `clock_rate()` or
  lambdas for params are acceptable; anything longer belongs in `scripts/`.
- Use the existing wildcards `{subtype}` (`h1n1|h3n2|vic`) and `{segment}`
  (`pb2 pb1 pa ha np na mp ns`, plus `genome`). Do not add subtypes,
  segments or targets to `rule all` without Tier 2 approval.
- Outputs go to `results/{subtype}/{segment}/...` (intermediate) or
  `auspice/{subtype}/...` (final). Never hard-code `source/` paths in new
  rules: use the variables in `ingest.smk` (`jhh_sequences`, ...).
- Filter thresholds must stay consistent across `segments.smk`,
  `genomes.smk` and `config/report.yaml` (`qc_min_coverage`,
  `qc_pass_status`). Change them together or not at all.
- After any `.smk` change: `snakemake -n --cores 1` (dry run) must succeed,
  `snakemake --lint` must show no new warnings, and regenerate
  `rulegraph.png` if the rule graph changed
  (`snakemake --rulegraph | dot -Tpng > rulegraph.png`).

## 6. Script conventions

- Every script that calculates or modifies metrics or data for the builds
  lives in `scripts/` (fludb's own scripts stay in `fludb/scripts/`).
- Start each script with a docstring: what it does, which rule calls it,
  inputs, outputs. Use `argparse` (CLI scripts) or the `snakemake` object
  (`script:` scripts); no hard-coded paths; print or log a short summary
  (rows read, rows written, rows dropped and why).
- Code is minimal, readable and commented: small named functions, no
  speculative options, no dead code, no new dependencies unless approved
  (Tier 3). Prefer pandas/Biopython already in `environment.yml`.
- Fail loudly: exit non-zero on bad input rather than writing partial output.
- Retired scripts move to `scripts/depreciated/`; nothing there is called.
- `scripts/report.py`: add a plot or table as an `item_*` function and
  register it in `report_layout()`; it then appears in the HTML report, the
  deck and the exports.
- `scripts/run_report.py` (per-machine run benchmarking) is separate from the
  surveillance report; change it only when asked.

## 7. Verify before you hand back

Run what applies and report the results to the user:

1. `bash scripts/data_guard.sh` reports OK.
2. `snakemake -n --cores 1` succeeds (production) and
   `snakemake -n --cores 1 --configfile config/tutorial.yaml` succeeds.
3. Tier 2-3: a full tutorial run succeeds
   (`snakemake --profile profiles/default --cores 4 --configfile config/tutorial.yaml`,
   on a clean workspace), and you compare before/after: sequences kept per
   build (`results/*/*/filter_log.tsv`, `filtered.tsv` row counts), tip counts
   in `auspice/`, and any report table that changed. State the differences.
4. Environment changes: `bash scripts/build_env.sh --check`.
5. `git diff` reviewed with the user; nothing outside the planned files changed.
6. Documentation parity checked (section 8) and reported.

Never claim a test passed that you did not run.

## 8. Documentation parity (required)

Every code change (new feature, bug fix, refactor, parameter change) **must**
come with matching documentation updates **in the same piece of work**:

- the wiki page(s) for what you changed (table below);
- the repository `README.md` if the change affects setup, usage or the
  top-level DAG;
- every mermaid diagram whose workflow you changed (and `rulegraph.png` if
  the rule graph changed).

| If you change... | Update these wiki pages |
|---|---|
| `source_prep/`, `scripts/prepare_source.py` | Step-1-Source-Data-Preparation, Tutorial-2-Adding-a-New-Sequencing-Run |
| `fludb/scripts/upload_vaccine.py`, vaccine header format | Step-1-Source-Data-Preparation, Tutorial-3-Updating-Vaccine-Strains |
| `ingest.smk`, flusort, other `fludb/` scripts | Step-3-Filtering-and-Quality-Control, Snakemake-and-Scripts-Reference, Pipeline-Overview |
| Filters (`--query`, `min_lengths`, `config/exclude.tsv` rules), clock rates, Nextclade datasets | Step-3-Filtering-and-Quality-Control |
| `Snakefile` (`rule all`, wildcards), `profiles/`, run options in `config/*.yaml`, `snapshot.smk`, `snapshot_clean.sh` | Step-2-Running-the-Pipeline, Snakemake-and-Scripts-Reference |
| Other steps in `segments.smk` / `genomes.smk` | Snakemake-and-Scripts-Reference, Pipeline-Overview |
| `reports.smk`, `scripts/report.py`, `scripts/run_report.py`, `config/report.yaml` | Step-4-Reports-and-Outputs |
| Upload scripts, `config/description.md`, `config/*/auspice_config.json` | Step-5-Reviewing-and-Publishing-Builds |
| `scripts/data_guard.sh`, `.githooks/`, `.gitignore`, folder layout | Data-Protection |
| `workflow/envs/environment.yml`, `scripts/build_env.sh` | Getting-Started |
| `tutorial/`, `config/tutorial.yaml`, `scripts/generate_tutorial_dataset.py` | Tutorial-1-Your-First-Build |
| Any new, renamed or retired script | Snakemake-and-Scripts-Reference (script inventory) |
| Workflow structure (stages, rule order, a new `.smk`) | Mermaid diagrams on Home, Pipeline-Overview and the relevant Step page; repo `README.md` |
| New terms | Glossary |
| These agent rules | `.agents/AGENTS.md` and Coding-with-Agents |
| A known bug fixed or found | Roadmap-and-Known-Issues |

Rules:

- Write each fact in **one** place; link to it from elsewhere instead of
  repeating it. Keep each page's "Troubleshooting / FAQ" and "Next step →"
  ending.
- In your final message, **list every doc you updated, and every doc you
  checked and left unchanged with the reason** (e.g. "Step 4: unchanged,
  report outputs unaffected").
- Work is **not complete** until documentation parity is verified. If you
  cannot edit the wiki (not cloned, no access), say so explicitly and give the
  user the exact text to paste; do not report the task as done.
- Wiki edits follow the same git rules (section 9): never stage, commit or
  push the wiki unless the user explicitly asks.

## 9. Git

- Do not stage or commit until the user explicitly asks. Then stage only the
  files you changed, by name (never `git add .` or `git add -A`).
- Commit messages: a summary line in the imperative (max ~72 characters),
  a blank line, then a body that says **what changed, why, and what it does
  to the builds or outputs**, as `-` bullets when there are several points.
  Name rules, files and thresholds explicitly; mention data-format or output
  changes and anything the next person must do (rebuild env, rerun ingest).
  Match the style of `git log`.
- One logical change per commit. Never commit generated outputs, data,
  notebooks with outputs, or secrets.
- If the pre-commit or pre-push hook blocks you, do not work around it.

## 10. Nextstrain uploads and sharing

Never upload, never print upload commands as a step you will run, never
publish reports. Builds go to `nextstrain.org/groups/PekoszLab` (private) and
`PekoszLab-Public` only after a person has inspected them in Auspice
([Step 5](https://github.com/Pekosz-Lab/nextstrain/wiki/Step-5-Reviewing-and-Publishing-Builds)). The surveillance report is
confidential and internal.

## 11. Attribution (do not remove)

`scripts/report.py` was designed and developed by **Elgin Akin**, with
assistance from Claude (Anthropic).

- Keep the authorship comment at the top of `scripts/report.py`.
- Keep the `ATTRIBUTION` constant ("Developed by Elgin Akin, 2026") and its
  use in both outputs (HTML report and PowerPoint deck).
- Do not remove or weaken `verify_attribution()`; the report build is meant to
  fail if the attribution is missing from either output.
- "Developed by" (the author) is separate from "Prepared by" (whoever ran the
  pipeline); do not merge them.

## 12. Environment quick reference

- Build/check: `bash scripts/build_env.sh` / `--check` / `--help`
  (conda env `pekosz-nextstrain`, `workflow/envs/environment.yml`).
  This also enables the git hooks.
- Run: `conda activate pekosz-nextstrain`, then
  `snakemake --profile profiles/default --cores 8`
  (tutorial: add `--configfile config/tutorial.yaml`).
- Report by hand: `python scripts/report.py --help`.
