#!/usr/bin/env python3
"""
prepare_source.py: build the two JHH input files for the Nextstrain pipeline.

WHAT IT DOES
    Reads every sequencing-run FASTA in source_prep/runs/ and the run dates in
    source_prep/run_dates.csv, checks everything, and writes:

        source_prep/output/JHH_sequences.fasta   all runs combined and cleaned
        source_prep/output/JHH_metadata.txt      one row per specimen
        source_prep/output/prep_report.txt       everything it checked and found

    You then copy the first two files into source/ and run the pipeline.
    Step-by-step instructions for people: source_prep/README.md

HOW TO RUN (from the nextstrain folder)
    python scripts/prepare_source.py

    No options are needed. The last lines it prints say READY or STOPPED.

OPTIONS (normally not needed)
    --folder PATH            use a different prep folder instead of source_prep/
    --bootstrap-dates FILE   one-time setup: create run_dates.csv from an existing
                             JHH_metadata.txt (one row per run, with its date)

EXIT STATUS
    0 = READY (output written), 1 = STOPPED (something to fix), 2 = unexpected error

Uses only the Python standard library (Python 3.8 or newer), so it runs inside or
outside the pekosz-nextstrain conda environment.

Replaces scripts/jhh_unique_strains.py and the manual Excel/cat steps.
"""

import argparse
import csv
import datetime as dt
import getpass
import hashlib
import os
import platform
import re
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path

# =============================================================================
# SETTINGS: everything you might ever need to change is here
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
PREP_FOLDER = REPO_ROOT / "source_prep"          # holds runs/, run_dates.csv, output/
SOURCE_FOLDER = REPO_ROOT / "source"             # the pipeline's input folder (only compared, never written)
EXCLUDE_FILE = REPO_ROOT / "config" / "exclude.tsv"

OUTPUT_SEQUENCES = "JHH_sequences.fasta"
OUTPUT_METADATA = "JHH_metadata.txt"
OUTPUT_REPORT = "prep_report.txt"

PASSAGE_HISTORY = "vtm"                          # viral transport medium; same for every specimen
METADATA_COLUMNS = ["sequence_ID", "sample_ID", "sequencing_run", "date", "passage_history"]

FASTA_EXTENSIONS = (".fasta", ".fa", ".fas", ".fna")
FASTA_LINE_WIDTH = 60
SEGMENTS = (1, 2, 3, 4, 5, 6, 7, 8)

# Minimum lengths used by the pipeline (Snakefile `min_lengths`), by segment number.
# Segments 1 and 2 swap names between flu A and flu B but share the same minimum.
# Shorter segments are kept here; the pipeline drops them later. Reported only.
MIN_LENGTH = {1: 2000, 2: 2000, 3: 1800, 4: 1400, 5: 1200, 6: 1200, 7: 700, 8: 700}
HIGH_N_FRACTION = 0.10           # report segments that are more than 10% N
CONTROL_SEQUENCE_LENGTH = 200    # a control with a segment this long likely has real (contaminating) sequence
EARLIEST_YEAR = 2015             # dates before this are treated as typing mistakes

# Run names look like IV26Run8 (IV + 2-digit year + Run + number, optional letter: IV25Run11b).
# The letter is only accepted when no other letter follows it, so "IV26Run7final"
# is run IV26Run7 and the control "IV26Run5bNTC" belongs to run IV26Run5.
RUN_NAME = re.compile(r"IV(\d{2})Run0*(\d{1,3})([A-Za-z](?![A-Za-z]))?", re.IGNORECASE)
# A FASTA header is <specimen ID>_<segment number>, e.g. JH23840_4.
# No underscores inside the ID: later pipeline steps split the header on "_".
HEADER = re.compile(r"(?P<id>[A-Za-z0-9.\-]+)_(?P<segment>\d+)")
SPECIMEN_ID = re.compile(r"JH(\d{2})\d+")        # JH + 2-digit year + number, e.g. JH25583
# Negative/positive controls are named after the run, e.g. IV25Run6NTC.
CONTROL_NAME = re.compile(r"NTC|NEG|BLANK|WATER|H2O|CTRL|CONTROL|PTC|POS", re.IGNORECASE)
IUPAC_BASES = set("ACGTRYSWKMBDHVN")

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%d-%b-%Y", "%d-%b-%y",
                "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%Y.%m.%d")

TOTAL_STEPS = 7
RULE = "=" * 78


# =============================================================================
# Messages: printed to the console and kept for prep_report.txt
# =============================================================================

class Log:
    """Prints every message and remembers it for the report.

    [OK]       all good
    [NOTE]     information, nothing to do
    [FIXED]    the script corrected a harmless formatting problem
    [WARNING]  the script handled it, but a person should read it
    [PROBLEM]  must be fixed; nothing is written until it is
    """

    CONSOLE_LIST_LIMIT = 10   # long lists are shortened on screen; the report has them in full

    def __init__(self):
        self.report_lines = []
        self.warnings = []
        self.problems = []    # (what is wrong, how to fix it)

    def say(self, text="", console=True):
        if console:
            print(text, flush=True)
        self.report_lines.append(text)

    def step(self, number, title):
        self.say()
        self.say(f"STEP {number} of {TOTAL_STEPS}: {title}")
        self.say("-" * 78)

    def ok(self, text):
        self.say(f"  [OK]      {text}")

    def note(self, text, details=()):
        self.say(f"  [NOTE]    {text}")
        self.details(details)

    def fixed(self, text, details=()):
        self.say(f"  [FIXED]   {text}")
        self.details(details)

    def warn(self, text, details=()):
        self.warnings.append(text)
        self.say(f"  [WARNING] {text}")
        self.details(details)

    def problem(self, text, fix, details=()):
        self.problems.append((text, fix))
        self.say(f"  [PROBLEM] {text}")
        self.say(f"            HOW TO FIX: {fix}")
        self.details(details)

    def details(self, items):
        items = list(items)
        for i, item in enumerate(items):
            self.say(f"              - {item}", console=i < self.CONSOLE_LIST_LIMIT)
        hidden = len(items) - self.CONSOLE_LIST_LIMIT
        if hidden > 0:
            print(f"              ... and {hidden} more (full list in {OUTPUT_REPORT})")

    def table(self, header, rows):
        widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
        for row in [header, ["-" * w for w in widths]] + list(rows):
            self.say("    " + "  ".join(str(x).ljust(w) for x, w in zip(row, widths)).rstrip())


def rel(path):
    """Path relative to the nextstrain folder, for short readable messages."""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def plural(n, word, plural_word=None):
    return f"{n} {word if n == 1 else (plural_word or word + 's')}"


def verb(n, singular, plural_form):
    """verb(1, 'is', 'are') -> 'is'; verb(3, 'is', 'are') -> 'are'."""
    return singular if n == 1 else plural_form


def natural_key(text):
    """Sort JH2597 before JH25583 and Run9 before Run10."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


# =============================================================================
# Run names and dates
# =============================================================================

def parse_run_name(text):
    """Return the standard run name found in `text` (e.g. 'IV26Run8'), or None."""
    match = RUN_NAME.search(text)
    if not match:
        return None
    year, number, letter = match.groups()
    return f"IV{year}Run{int(number)}{(letter or '').lower()}"


def run_sort_key(run_name):
    """IV25Run9 < IV25Run10 < IV25Run11 < IV25Run11b < IV26Run1."""
    year, number, letter = RUN_NAME.fullmatch(run_name).groups()
    return int(year), int(number), (letter or "").lower()


def run_year(run_name):
    return 2000 + int(run_name[2:4])


def parse_date(text):
    """Read a date typed by a person or saved by Excel. Returns a date or None."""
    text = text.strip()
    text = re.sub(r"[ T]\d{1,2}:\d{2}(:\d{2})?(\s*[AaPp][Mm])?$", "", text).strip()  # drop a time
    if re.fullmatch(r"\d{5}", text):                    # Excel serial day number, e.g. 46301
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(text))
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


# =============================================================================
# STEP 1: find the run files
# =============================================================================

class Run:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.date = None
        self.records = {}          # (specimen, segment) -> sequence
        self.md5 = ""

    @property
    def specimens(self):
        return {specimen for specimen, _ in self.records}


def find_run_files(runs_dir, log):
    log.step(1, f"Looking for run FASTA files in {rel(runs_dir)}/")
    if not runs_dir.is_dir():
        # git does not track this folder (it holds private data), so a fresh clone
        # may not have it yet. Create it so the user only has to drop files in.
        runs_dir.mkdir(parents=True, exist_ok=True)
        log.problem(f"The folder {rel(runs_dir)}/ did not exist, so it was created (empty).",
                    "Copy the run FASTA files (ConsensusIV##Run#.fasta) from the lab SharePoint folder "
                    f"into {rel(runs_dir)}/, then run this script again.")
        return {}

    files_per_run = defaultdict(list)
    for path in sorted(runs_dir.iterdir(), key=lambda p: natural_key(p.name)):
        name = path.name
        if name.startswith(".") or name.startswith("~$") or name in ("Thumbs.db", "desktop.ini"):
            continue                                    # hidden, system and Office lock files
        if path.is_dir():
            inside = [p for p in path.rglob("*") if p.suffix.lower() in FASTA_EXTENSIONS]
            if inside:
                log.problem(f"The folder runs/{name}/ contains FASTA files. Files inside folders are not read.",
                            "Move the run's FASTA file itself into runs/ (not the folder it came in), "
                            f"then delete the folder runs/{name}/.",
                            [rel(p) for p in inside])
            else:
                log.warn(f"Ignoring the folder runs/{name}/ (no FASTA files in it). You can delete it.")
            continue
        if path.suffix.lower() not in FASTA_EXTENSIONS:
            log.warn(f"Ignoring runs/{name}: not a FASTA file (only files ending in .fasta are read). "
                     "Please move it out of runs/.")
            continue
        run_name = parse_run_name(name)
        if run_name is None:
            log.problem(f"Cannot find a run name in the file name runs/{name}.",
                        "Rename the file to Consensus<run name>.fasta, for example ConsensusIV26Run8.fasta. "
                        f"If this is an old combined {OUTPUT_SEQUENCES}, remove it from runs/: only "
                        "single-run files belong there.")
            continue
        files_per_run[run_name].append(path)

    runs = {}
    for run_name, paths in files_per_run.items():
        if len(paths) > 1:
            log.problem(f"{len(paths)} files are for the same run {run_name}.",
                        "Keep only ONE file per run in runs/. If you are not sure which one is right, "
                        "ask the person who did the sequencing.",
                        [rel(p) for p in paths])
            continue
        runs[run_name] = Run(run_name, paths[0])
        if paths[0].name != f"Consensus{run_name}.fasta":
            log.note(f"runs/{paths[0].name} is read as run {run_name} "
                     f"(the usual name would be Consensus{run_name}.fasta; no need to rename).")

    if not runs and not log.problems:
        log.problem(f"There are no run FASTA files in {rel(runs_dir)}/.",
                    "Copy the run FASTA files (ConsensusIV##Run#.fasta) from the lab SharePoint folder "
                    f"into {rel(runs_dir)}/.")
    if runs:
        ordered = sorted(runs, key=run_sort_key)
        log.ok(f"Found {plural(len(runs), 'run file')}: {ordered[0]} to {ordered[-1]}.")
        log.details(ordered)
    return runs


# =============================================================================
# STEP 2: read run_dates.csv
# =============================================================================

def read_run_dates(dates_path, runs, log):
    log.step(2, f"Reading the run dates in {rel(dates_path)}")
    template = "sequencing_run,date,notes"
    if not dates_path.is_file():
        excel = [p for p in dates_path.parent.glob("run_dates*.xls*") if not p.name.startswith("~$")]
        if excel:
            log.problem(f"Found {excel[0].name} but not {dates_path.name}. The script can only read CSV files.",
                        f"Open {excel[0].name} in Excel, choose File > Save As, pick the format "
                        f"'CSV UTF-8 (Comma delimited)' and save it as {dates_path.name} in {rel(dates_path.parent)}/.")
        else:
            log.problem(f"{rel(dates_path)} does not exist.",
                        f"Copy run_dates.csv from the lab SharePoint folder into {rel(dates_path.parent)}/.")
        return {}

    raw = dates_path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")        # Excel on Windows: "CSV (Comma delimited)"
        log.fixed("run_dates.csv is not UTF-8 (Windows Excel format); read it anyway.")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    numbered = [(i, line) for i, line in enumerate(lines, 1) if line.strip(" ,;\t")]   # skip empty rows
    if not numbered:
        log.problem("run_dates.csv is empty.",
                    f"The first line must be:  {template}   then one line per run, e.g.  IV26Run8,2026-10-06,")
        return {}

    header_line = numbered[0][1]
    delimiter = next((d for d in (",", "\t", ";") if d in header_line), ",")
    rows = list(csv.reader([line for _, line in numbered], delimiter=delimiter))
    header = [h.strip().lower().replace(" ", "_").replace("-", "_") for h in rows[0]]
    run_col = next((header.index(h) for h in ("sequencing_run", "run", "run_name") if h in header), None)
    date_col = next((header.index(h) for h in ("date", "run_date") if h in header), None)
    notes_col = header.index("notes") if "notes" in header else None
    if run_col is None or date_col is None:
        log.problem(f"The first line of run_dates.csv must name the columns. It is: {header_line!r}",
                    f"Make the first line exactly:  {template}")
        return {}

    dates, notes, seen = {}, {}, {}
    bad_date = set()            # runs whose date was already reported as wrong
    today = dt.date.today()
    for (line_no, _), row in zip(numbered[1:], rows[1:]):
        cell = lambda col: row[col].strip() if col is not None and col < len(row) else ""
        run_text, date_text = cell(run_col), cell(date_col)
        where = f"run_dates.csv line {line_no}"
        if not run_text and not date_text:
            continue
        run_name = parse_run_name(run_text)
        if run_name is None or RUN_NAME.sub("", run_text).strip():
            log.problem(f"{where}: {run_text!r} is not a run name.",
                        "Write the run name like IV26Run8 (IV + 2-digit year + Run + number), "
                        "exactly as in the run's FASTA file name.")
            continue
        if not date_text:
            continue            # a run listed ahead of time; a missing date only matters once its file is in runs/
        date = parse_date(date_text)
        if date is None or date > today or date.year < EARLIEST_YEAR:
            bad_date.add(run_name)
        if date is None:
            log.problem(f"{where}: the date for {run_name} ({date_text!r}) cannot be read.",
                        "Write the date as YYYY-MM-DD, for example 2026-10-06.")
            continue
        if date > today:
            log.problem(f"{where}: the date for {run_name} ({date}) is in the future.",
                        "Check the date and correct it (YYYY-MM-DD).")
            continue
        if date.year < EARLIEST_YEAR:
            log.problem(f"{where}: the date for {run_name} ({date}) is before {EARLIEST_YEAR}.",
                        "Check the date and correct it (YYYY-MM-DD).")
            continue
        if date.year not in (run_year(run_name), run_year(run_name) - 1):
            log.warn(f"{where}: {run_name} is a {run_year(run_name)} run but its date is {date}. "
                     "Please check the date.")
        if date_text != date.isoformat():
            log.fixed(f"{where}: date {date_text!r} read as {date.isoformat()}.")
        if run_name in seen:
            if dates[run_name] != date:
                log.problem(f"{run_name} is listed twice in run_dates.csv with different dates "
                            f"({dates[run_name]} on line {seen[run_name]}, {date} on line {line_no}).",
                            f"Delete the wrong line for {run_name} in run_dates.csv.")
            else:
                log.warn(f"{run_name} is listed twice in run_dates.csv (lines {seen[run_name]} and {line_no}, "
                         "same date). You can delete one of the lines.")
            continue
        seen[run_name] = line_no
        dates[run_name] = date
        notes[run_name] = cell(notes_col)

    missing = sorted((r for r in runs if r not in dates and r not in bad_date), key=run_sort_key)
    for run_name in missing:
        log.problem(f"Run {run_name} has a FASTA file but no date in run_dates.csv.",
                    f"Add this line at the bottom of run_dates.csv (with the real date):  "
                    f"{run_name},YYYY-MM-DD,")
    for run_name, run in runs.items():
        run.date = dates.get(run_name)
    # Runs are numbered in order, so a later run dated before an earlier one may be a typing mistake.
    out_of_order, latest = [], {}
    for run_name in sorted(dates, key=run_sort_key):
        year = run_year(run_name)
        if year in latest and dates[run_name] < latest[year][1]:
            out_of_order.append(f"{run_name} ({dates[run_name]}) is dated before "
                                f"{latest[year][0]} ({latest[year][1]})")
        if year not in latest or dates[run_name] >= latest[year][1]:
            latest[year] = (run_name, dates[run_name])
    if out_of_order:
        log.note(f"{plural(len(out_of_order), 'run')} {verb(len(out_of_order), 'is', 'are')} dated earlier "
                 "than a lower-numbered run of the same year. Fine if that is true; otherwise fix the date:",
                 out_of_order)
    unused = sorted((r for r in dates if r not in runs), key=run_sort_key)
    if unused:
        log.note(f"{plural(len(unused), 'run')} in run_dates.csv {verb(len(unused), 'has', 'have')} no FASTA "
                 "file in runs/ "
                 "(fine if those files have not been added yet):", unused)
    found = sum(r in dates for r in runs)
    if runs and found == len(runs):
        log.ok(f"Every run file has a date ({len(dates)} {'run' if len(dates) == 1 else 'runs'} listed).")
    elif runs:
        log.say(f"  {found} of {len(runs)} run files have a date.")
    return notes


# =============================================================================
# STEP 3: read and check each run FASTA
# =============================================================================

def read_run_fasta(run, log):
    """Read one run file into run.records. Problems with single records are
    handled (record skipped or fixed) and reported; only an unusable file stops."""
    path, label = run.path, f"{run.name} ({run.path.name})"
    raw = path.read_bytes()
    run.md5 = hashlib.md5(raw).hexdigest()
    if not raw.strip():
        log.problem(f"{label}: the file is empty.",
                    "Copy the file again from SharePoint. If SharePoint shows a cloud icon, wait for the "
                    "download to finish (or choose 'Always keep on this device') before copying.")
        return
    if b"\x00" in raw[:4096]:
        log.problem(f"{label}: this is not a text FASTA file (it looks like an Excel, Word or zip file "
                    "renamed to .fasta).",
                    "Copy the original consensus FASTA from the sequencing folder again. Do not open "
                    "or save it in Excel or Word.")
        return
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
        log.fixed(f"{label}: unusual text encoding; read it anyway.")

    fixes = Counter()
    if "\r" in text:
        fixes["Windows line endings converted"] += text.count("\r")
        text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split into (line number, header, sequence lines).
    entries = []
    for line_no, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            entries.append([line_no, stripped[1:].strip(), []])
        elif not entries:
            log.problem(f"{label}: the file does not start with a FASTA header (a line starting with '>'). "
                        f"Line {line_no} is: {stripped[:60]!r}",
                        "This is not a FASTA file, or it was changed by another program. Copy the original "
                        "consensus FASTA from the sequencing folder again.")
            return
        else:
            entries[-1][2].append(stripped)

    bad_header, bad_segment, empty, bad_chars, conflicts, year_mismatch = [], [], [], [], [], []
    for line_no, header, seq_lines in entries:
        token = re.split(r"[\s|]", header, maxsplit=1)[0]
        if token != header:
            fixes["text after the sequence name removed from headers"] += 1
        match = HEADER.fullmatch(token)
        if not match:
            bad_header.append(f"line {line_no}: >{header}")
            continue
        specimen, segment = match.group("id"), int(match.group("segment"))
        if re.fullmatch(r"jh\d+", specimen, re.IGNORECASE) and not specimen.startswith("JH"):
            specimen = "JH" + specimen[2:]
            fixes["lower-case 'jh' in IDs changed to 'JH'"] += 1
        if segment not in SEGMENTS:
            bad_segment.append(f"line {line_no}: >{header} (segment {segment}; must be 1 to 8)")
            continue
        sequence = "".join(seq_lines)
        if re.search(r"\s", sequence):
            sequence = re.sub(r"\s", "", sequence)
            fixes["spaces inside sequences removed"] += 1
        if sequence != sequence.upper():
            sequence = sequence.upper()
            fixes["lower-case bases changed to upper case"] += 1
        if "-" in sequence or "." in sequence:
            sequence = sequence.replace("-", "").replace(".", "")
            fixes["gap characters (- or .) removed from sequences"] += 1
        if not sequence:
            empty.append(f"line {line_no}: >{header}")
            continue
        illegal = sorted(set(sequence) - IUPAC_BASES)
        if illegal:
            bad_chars.append(f"line {line_no}: >{header} contains {' '.join(illegal)}")
            continue
        year = SPECIMEN_ID.fullmatch(specimen)
        if year and 2000 + int(year.group(1)) not in (run_year(run.name), run_year(run.name) - 1):
            year_mismatch.append(specimen)
        key = (specimen, segment)
        if key in run.records:
            previous = run.records[key]
            if previous == sequence:
                fixes["exact duplicate records removed"] += 1
            else:
                keep = max((previous, sequence), key=lambda s: len(s) - s.count("N"))
                conflicts.append(f"{specimen}_{segment}: two different sequences "
                                 f"({len(previous)} and {len(sequence)} bases); kept the {len(keep)}-base one")
                run.records[key] = keep
            continue
        run.records[key] = sequence

    total = len(entries)
    for fix, count in sorted(fixes.items()):
        log.fixed(f"{label}: {fix} ({count}).")
    skipped = len(bad_header) + len(bad_segment) + len(empty) + len(bad_chars)
    if bad_header:
        log.warn(f"{label}: {plural(len(bad_header), 'sequence')} skipped because the name is not "
                 "<ID>_<segment number> (for example JH23840_4):", bad_header)
    if bad_segment:
        log.warn(f"{label}: {plural(len(bad_segment), 'sequence')} skipped because the segment number "
                 "is not 1 to 8:", bad_segment)
    if empty:
        log.warn(f"{label}: {plural(len(empty), 'sequence')} skipped (empty: a name with no bases):", empty)
    if bad_chars:
        log.warn(f"{label}: {plural(len(bad_chars), 'sequence')} skipped (characters that are not DNA "
                 "bases):", bad_chars)
    if conflicts:
        log.warn(f"{label}: {plural(len(conflicts), 'segment')} {verb(len(conflicts), 'appears', 'appear')} "
                 "twice in this file with different sequences:", conflicts)
    if year_mismatch:
        log.warn(f"{label}: {plural(len(year_mismatch), 'specimen ID')} "
                 f"{verb(len(year_mismatch), 'does', 'do')} not match the run year "
                 f"{run_year(run.name)} (JH + 2-digit year). Check that this is the right file:",
                 sorted(set(year_mismatch), key=natural_key))
    if not run.records:
        log.problem(f"{label}: no usable sequences in this file.",
                    "Check that this is the run's consensus FASTA. Copy the original again from the "
                    "sequencing folder; ask the sequencing team if the file itself is broken.")
    elif skipped > total / 2:
        log.problem(f"{label}: {skipped} of {total} sequences could not be used. This does not look like a "
                    "JHH consensus FASTA.",
                    "Check that you copied the right file from the sequencing folder.")
    else:
        log.ok(f"{label}: {plural(len(run.records), 'segment')} from "
               f"{plural(len(run.specimens), 'specimen')}.")


def read_all_runs(runs, log):
    log.step(3, "Reading and checking each run file")
    if not runs:
        log.say("  (no run files to read)")
    for run_name in sorted(runs, key=run_sort_key):
        read_run_fasta(runs[run_name], log)


# =============================================================================
# STEP 4: combine runs, set controls aside, resolve re-sequenced specimens
# =============================================================================

def read_exclude_list():
    if not EXCLUDE_FILE.is_file():
        return set()
    ids = set()
    for line in EXCLUDE_FILE.read_text(errors="replace").splitlines():
        value = line.split("\t")[0].split("#")[0].strip()
        if value and value.lower() not in ("strain", "sequence_id", "sample_id"):
            ids.add(value)
    return ids


def is_control(specimen):
    return not SPECIMEN_ID.fullmatch(specimen) and bool(CONTROL_NAME.search(specimen))


def combine_runs(runs, log):
    """Returns {specimen: run name} for the specimens that go into the output."""
    log.step(4, "Combining runs: controls, re-sequenced specimens and unusual IDs")
    per_specimen = defaultdict(lambda: defaultdict(dict))     # specimen -> run -> segment -> sequence
    for run in runs.values():
        for (specimen, segment), sequence in run.records.items():
            per_specimen[specimen][run.name][segment] = sequence

    chosen, controls, resequenced, unusual = {}, {}, [], []
    for specimen, by_run in per_specimen.items():
        if is_control(specimen):
            controls[specimen] = by_run
            continue
        if not SPECIMEN_ID.fullmatch(specimen):
            unusual.append(specimen)
        # Keep the run with the most segments; if equal, the most recent run.
        best = max(by_run, key=lambda r: (len(by_run[r]), run_sort_key(r)))
        chosen[specimen] = best
        if len(by_run) > 1:
            found = ", ".join(f"{r} ({len(by_run[r])} segments)" for r in sorted(by_run, key=run_sort_key))
            resequenced.append(f"{specimen}: in {found} -> using {best}")

    # Controls never go into the output (they are not patient specimens), but
    # a control that produced real sequence means possible contamination.
    if controls:
        contaminated, clean = [], []
        for specimen in sorted(controls, key=natural_key):
            for run_name, segments in sorted(controls[specimen].items(), key=lambda x: run_sort_key(x[0])):
                longest = max(len(s) for s in segments.values())
                text = (f"{specimen} in {run_name}: {plural(len(segments), 'segment')} "
                        f"(longest {longest} bases)")
                named_run = parse_run_name(specimen)
                if named_run and named_run != run_name:
                    text += f"; its name says run {named_run}"
                (contaminated if longest >= CONTROL_SEQUENCE_LENGTH else clean).append(text)
        if contaminated:
            log.warn(f"POSSIBLE CONTAMINATION: {plural(len(contaminated), 'negative control')} produced "
                     f"sequence of {CONTROL_SEQUENCE_LENGTH}+ bases. Tell the sequencing team and Dr. Pekosz; "
                     "specimens from these runs may need checking. Controls are left out of the output:",
                     contaminated)
        if clean:
            log.note(f"{plural(len(clean), 'control')} with only short fragments (normal). "
                     "Left out of the output:", clean)
    else:
        log.ok("No negative controls (NTC, water, ...) found in the run files.")

    if resequenced:
        log.note(f"{plural(len(resequenced), 'specimen')} {verb(len(resequenced), 'was', 'were')} sequenced "
                 "in more than one run. Each keeps ONE run: the one with the most segments (if equal, the most recent run):", resequenced)
    else:
        log.ok("No specimen appears in more than one run.")

    if unusual:
        log.warn(f"{plural(len(unusual), 'ID')} {verb(len(unusual), 'does', 'do')} not look like a JH specimen "
                 "ID or a control. Kept in the output; check it is a real specimen:", sorted(unusual, key=natural_key))

    excluded = sorted(read_exclude_list() & set(chosen), key=natural_key)
    if excluded:
        log.note(f"{plural(len(excluded), 'specimen')} {verb(len(excluded), 'is', 'are')} listed in "
                 f"{rel(EXCLUDE_FILE)}: kept here, removed later by the pipeline:", excluded)

    log.ok(f"{plural(len(chosen), 'specimen')} will go into the output "
           f"({plural(len(controls), 'control')} left out).")
    return chosen


# =============================================================================
# STEP 5: quality summary
# =============================================================================

def quality_summary(runs, chosen, log):
    log.step(5, "Quality summary (for information; the pipeline filters further)")
    by_run = defaultdict(list)
    for specimen, run_name in chosen.items():
        by_run[run_name].append(specimen)

    rows, segment_counts = [], Counter()
    short, high_n, ambiguous = Counter(), Counter(), 0
    for run_name in sorted(runs, key=run_sort_key):
        run = runs[run_name]
        complete = 0
        for specimen in by_run.get(run_name, []):
            segments = [seg for seg in SEGMENTS if (specimen, seg) in run.records]
            segment_counts[len(segments)] += 1
            complete += len(segments) == 8
            for seg in segments:
                seq = run.records[(specimen, seg)]
                short[seg] += len(seq) < MIN_LENGTH[seg]
                high_n[seg] += seq.count("N") > HIGH_N_FRACTION * len(seq)
                ambiguous += sum(seq.count(b) for b in "RYSWKMBDHV")
        n = len(by_run.get(run_name, []))
        rows.append([run_name, run.date or "MISSING", n, complete, n - complete, run.path.name])

    log.table(["run", "date", "specimens", "complete (8/8)", "partial", "file"], rows)
    total = len(chosen)
    complete = segment_counts[8]
    log.say()
    log.say(f"  Specimens: {total}   complete genomes (8 segments): {complete}"
            f" ({100 * complete / total:.0f}%)" if total else "  Specimens: 0")
    if total:
        log.say("  Segments per specimen: " +
                ", ".join(f"{k} segs: {segment_counts[k]}" for k in sorted(segment_counts, reverse=True)))
        if sum(short.values()):
            log.note(f"{sum(short.values())} segments are shorter than the pipeline's minimum length and will "
                     "be dropped by the pipeline (by segment number: " +
                     ", ".join(f"{s}: {short[s]}" for s in SEGMENTS if short[s]) + ").")
        if sum(high_n.values()):
            log.note(f"{sum(high_n.values())} segments are more than {HIGH_N_FRACTION:.0%} N (low coverage).")
        if ambiguous:
            log.note(f"{ambiguous} ambiguous bases (R, Y, K, M, S, W, ...) in total. Normal in small numbers.")


# =============================================================================
# STEP 6: compare with what is in source/ now
# =============================================================================

def read_metadata_ids(path):
    """Return {sequence_ID: sequencing_run} from a JHH_metadata.txt (tolerant reader)."""
    text = path.read_bytes().decode("utf-8-sig", errors="replace").replace("\r", "")
    rows = list(csv.reader(text.splitlines(), delimiter="\t"))
    if not rows or "sequence_ID" not in rows[0]:
        return None
    id_col = rows[0].index("sequence_ID")
    run_col = rows[0].index("sequencing_run") if "sequencing_run" in rows[0] else None
    return {r[id_col].strip(): (r[run_col].strip() if run_col is not None and run_col < len(r) else "")
            for r in rows[1:] if len(r) > id_col and r[id_col].strip()}


def compare_with_source(chosen, log):
    log.step(6, f"Comparing with the files in {rel(SOURCE_FOLDER)}/ now")
    if not chosen:
        log.say("  (skipped: there are no specimens to compare yet)")
        return
    current = SOURCE_FOLDER / OUTPUT_METADATA
    if not current.is_file():
        log.note(f"There is no {rel(current)} yet, so there is nothing to compare with.")
        return
    old = read_metadata_ids(current)
    if old is None:
        log.warn(f"{rel(current)} has no 'sequence_ID' column, so it cannot be compared. It will be "
                 "replaced when you copy the new files in.")
        return
    new_ids, old_ids = set(chosen), set(old)
    added = sorted(new_ids - old_ids, key=natural_key)
    removed = sorted(old_ids - new_ids, key=natural_key)
    moved = sorted((s for s in new_ids & old_ids if old[s] and old[s] != chosen[s]), key=natural_key)
    log.say(f"  Now in source/: {len(old_ids)} specimens.   New output: {len(new_ids)} specimens.")
    if added:
        per_run = Counter(chosen[s] for s in added)
        log.note(f"{plural(len(added), 'specimen')} {verb(len(added), 'is', 'are')} NEW compared with "
                 "source/ (by run: " +
                 ", ".join(f"{r}: {per_run[r]}" for r in sorted(per_run, key=run_sort_key)) + "):", added)
    if removed:
        log.warn(f"{plural(len(removed), 'specimen')} in source/ now will NOT be in the new files. Expected for "
                 "rows that never had sequences or for controls; otherwise check that every run file is in runs/:",
                 [f"{s} ({old[s] or 'no run'})" for s in removed])
    if moved:
        log.note(f"{plural(len(moved), 'specimen')} {verb(len(moved), 'changes', 'change')} run compared "
                 "with source/:",
                 [f"{s}: {old[s]} -> {chosen[s]}" for s in moved])
    if not (added or removed or moved):
        log.ok("Same specimens as the files in source/ now.")


# =============================================================================
# STEP 7: write the output files
# =============================================================================

def write_atomically(path, text):
    """Write to a temporary file first, then swap it in: never a half-written file."""
    temporary = path.with_name(path.name + ".partial")
    with open(temporary, "w", newline="\n", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(temporary, path)


def write_outputs(runs, chosen, output_dir, log):
    log.step(7, f"Writing the output files to {rel(output_dir)}/")
    output_dir.mkdir(parents=True, exist_ok=True)
    sequences_path, metadata_path = output_dir / OUTPUT_SEQUENCES, output_dir / OUTPUT_METADATA

    if log.problems:
        for stale in (sequences_path, metadata_path):     # so nobody copies an out-of-date file
            try:
                stale.unlink()
                log.say(f"  Removed the old {rel(stale)} so it cannot be copied by mistake.")
            except FileNotFoundError:
                pass
            except OSError as error:
                log.warn(f"Could not remove the old {rel(stale)} ({error}). Do NOT copy it to source/.")
        log.say("  Nothing written: fix the problems listed below first.")
        return

    order = sorted(chosen, key=lambda s: (run_sort_key(chosen[s]), natural_key(s)))
    fasta, metadata, n_records = [], ["\t".join(METADATA_COLUMNS)], 0
    for specimen in order:
        run = runs[chosen[specimen]]
        for segment in SEGMENTS:
            sequence = run.records.get((specimen, segment))
            if sequence:
                fasta.append(f">{specimen}_{segment}")
                fasta.extend(sequence[i:i + FASTA_LINE_WIDTH] for i in range(0, len(sequence), FASTA_LINE_WIDTH))
                n_records += 1
        metadata.append("\t".join([specimen, specimen, run.name, run.date.isoformat(), PASSAGE_HISTORY]))
    write_atomically(sequences_path, "\n".join(fasta) + "\n")
    write_atomically(metadata_path, "\n".join(metadata) + "\n")

    # Read the files back to be sure they are complete and consistent.
    written_headers = [l[1:] for l in sequences_path.read_text().splitlines() if l.startswith(">")]
    written_ids = {h.rsplit("_", 1)[0] for h in written_headers}
    meta_ids = [l.split("\t")[0] for l in metadata_path.read_text().splitlines()[1:]]
    if len(written_headers) != n_records or written_ids != set(meta_ids) or len(meta_ids) != len(set(meta_ids)):
        log.problem("The output files did not read back correctly (disk full or folder not writable?).",
                    f"Check there is free disk space and that {rel(output_dir)}/ is not open in another "
                    "program, then run the script again.")
        return
    log.ok(f"{rel(sequences_path)}: {plural(n_records, 'sequence')} from {plural(len(order), 'specimen')}.")
    log.ok(f"{rel(metadata_path)}: {plural(len(meta_ids), 'row')}, columns: {', '.join(METADATA_COLUMNS)}.")
    log.ok("Every specimen has exactly one metadata row and at least one sequence. "
           "sample_ID = sequence_ID, so every name is unique.")


# =============================================================================
# Report and final result
# =============================================================================

def finish(log, runs, prep_dir, output_dir, started):
    log.say()
    log.say(RULE)
    if log.problems:
        log.say(f"  RESULT: STOPPED  ({plural(len(log.problems), 'problem')} to fix; nothing was written)")
        log.say(RULE)
        for i, (text, fix) in enumerate(log.problems, 1):
            log.say(f"  {i}. {text}")
            log.say(f"     HOW TO FIX: {fix}")
        log.say()
        log.say("  Fix the problems above, then run the script again:  python scripts/prepare_source.py")
        log.say(f"  Stuck? Send {rel(output_dir / OUTPUT_REPORT)} to the pipeline maintainer.")
    else:
        extra = f"  ({plural(len(log.warnings), 'warning')}: please read them above)" if log.warnings else ""
        log.say(f"  RESULT: READY{extra}")
        log.say(RULE)
        log.say("  Next: copy these 2 files into the source/ folder (replace the old ones):")
        log.say(f"      {rel(output_dir / OUTPUT_SEQUENCES)}")
        log.say(f"      {rel(output_dir / OUTPUT_METADATA)}")
        log.say("  Then run the pipeline as described in the main README.")
    log.say(f"  Full report: {rel(output_dir / OUTPUT_REPORT)}")
    log.say(RULE)

    header = [
        "JHH source preparation report (scripts/prepare_source.py)",
        RULE,
        f"Date:      {started:%Y-%m-%d %H:%M:%S}",
        f"Run by:    {getpass.getuser()} on {platform.node()} ({platform.system()}, Python {platform.python_version()})",
        f"Folder:    {prep_dir}",
        f"Result:    {'STOPPED' if log.problems else 'READY'}"
        f"  ({plural(len(log.problems), 'problem')}, {plural(len(log.warnings), 'warning')})",
        "",
        "Input files (MD5 checksums identify the exact file used):",
    ]
    for run_name in sorted(runs, key=run_sort_key):
        run = runs[run_name]
        date = run.date.isoformat() if run.date else "no date"
        header.append(f"    {run_name:<12} {date:<10}  {run.md5 or '-':<32}  {run.path.name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_atomically(output_dir / OUTPUT_REPORT, "\n".join(header + [""] + log.report_lines) + "\n")
    return 1 if log.problems else 0


def prepare(prep_dir):
    started = dt.datetime.now()
    log = Log()
    runs_dir, dates_path, output_dir = prep_dir / "runs", prep_dir / "run_dates.csv", prep_dir / "output"
    log.say(RULE)
    log.say("  Preparing JHH_sequences.fasta and JHH_metadata.txt for the Nextstrain pipeline")
    log.say(f"  {started:%Y-%m-%d %H:%M}   folder: {rel(prep_dir)}/")
    log.say(RULE)

    runs = find_run_files(runs_dir, log)
    read_run_dates(dates_path, runs, log)
    read_all_runs(runs, log)
    runs = {name: run for name, run in runs.items() if run.records}
    chosen = combine_runs(runs, log)
    if all(run.date for run in runs.values()):
        quality_summary(runs, chosen, log)
    else:
        log.step(5, "Quality summary")
        log.say("  (skipped until every run has a date)")
    compare_with_source(chosen, log)
    write_outputs(runs, chosen, output_dir, log)
    return finish(log, runs, prep_dir, output_dir, started)


# =============================================================================
# One-time setup: create run_dates.csv from an existing JHH_metadata.txt
# =============================================================================

def bootstrap_dates(old_metadata, dates_path):
    if dates_path.exists():
        print(f"STOPPED: {rel(dates_path)} already exists; it was not changed. "
              "Delete or rename it first if you really want to rebuild it.")
        return 1
    text = Path(old_metadata).read_bytes().decode("utf-8-sig", errors="replace").replace("\r", "")
    rows = list(csv.DictReader(text.splitlines(), delimiter="\t"))
    if not rows or not {"sequencing_run", "date"} <= set(rows[0]):
        print(f"STOPPED: {old_metadata} needs 'sequencing_run' and 'date' columns (tab-separated).")
        return 1
    dates = defaultdict(set)
    for row in rows:
        run_name = parse_run_name(row["sequencing_run"] or "")
        date = parse_date(row["date"] or "")
        if run_name and date:
            dates[run_name].add(date)
    lines = ["sequencing_run,date,notes"]
    for run_name in sorted(dates, key=run_sort_key):
        found = sorted(dates[run_name])
        note = "copied from the old JHH_metadata.txt"
        if len(found) > 1:
            note += f"; it had several dates ({' '.join(d.isoformat() for d in found)}), the earliest is used"
        lines.append(f"{run_name},{found[0].isoformat()},{note}")
    dates_path.parent.mkdir(parents=True, exist_ok=True)
    write_atomically(dates_path, "\n".join(lines) + "\n")
    print(f"Wrote {rel(dates_path)} with {plural(len(dates), 'run')} from {old_metadata}. Check it, then run "
          "python scripts/prepare_source.py")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Build source_prep/output/JHH_sequences.fasta and JHH_metadata.txt from the run FASTAs "
                    "in source_prep/runs/ and the dates in source_prep/run_dates.csv. No options needed.")
    parser.add_argument("--folder", type=Path, default=PREP_FOLDER,
                        help=f"prep folder with runs/ and run_dates.csv (default: {rel(PREP_FOLDER)})")
    parser.add_argument("--bootstrap-dates", metavar="OLD_METADATA",
                        help="one-time setup: write run_dates.csv from an existing JHH_metadata.txt")
    args = parser.parse_args()
    prep_dir = args.folder.resolve()
    try:
        if args.bootstrap_dates:
            return bootstrap_dates(args.bootstrap_dates, prep_dir / "run_dates.csv")
        return prepare(prep_dir)
    except Exception:
        print()
        print(RULE)
        print("  RESULT: UNEXPECTED ERROR (this is a bug in the script, not something you did)")
        print(RULE)
        traceback.print_exc()
        print()
        print("  Please send everything printed above to the pipeline maintainer.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
