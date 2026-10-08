#!/usr/bin/env bash
# Build, check and lock the pekosz-nextstrain conda environment.
# Run from anywhere inside the repository:
#
#   bash scripts/build_env.sh                  create the environment (or update it if it
#                                              exists), then check it
#   bash scripts/build_env.sh --recreate       delete it and rebuild from scratch, then check
#   bash scripts/build_env.sh --locked         rebuild with the exact versions in
#                                              workflow/envs/conda-lock.yml, then check
#   bash scripts/build_env.sh --check          only run the checks
#   bash scripts/build_env.sh --check --network   ...and also test a Nextclade download
#   bash scripts/build_env.sh --lock           regenerate workflow/envs/conda-lock.yml
#                                              (needs conda-lock: pipx install conda-lock)
#
# Extra options:
#   --intel        Apple Silicon only: build an Intel (osx-64) env that runs under Rosetta 2
#   --name NAME    use another environment name (default: pekosz-nextstrain)
#
# The environment itself is defined in workflow/envs/environment.yml.
# Works on macOS (Apple Silicon / Intel) and Linux, including Windows via WSL2.
# Needs conda >= 23.10 (Miniforge recommended) or mamba / micromamba.
set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$PWD"
THIS_SCRIPT="$REPO/scripts/build_env.sh"
ENV_FILE="workflow/envs/environment.yml"
LOCK_FILE="workflow/envs/conda-lock.yml"

# ============================================================================
# Options
# ============================================================================
NAME="pekosz-nextstrain"
MODE="build"        # build | recreate | locked | check | lock | checks-in-env
INTEL=0
NETWORK=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --recreate) MODE="recreate" ;;
        --locked)   MODE="locked" ;;
        --check)    MODE="check" ;;
        --lock)     MODE="lock" ;;
        --network)  NETWORK=1 ;;
        --intel)    INTEL=1 ;;
        --name)     NAME="$2"; shift ;;
        --checks-in-env) MODE="checks-in-env" ;;   # internal: used by --check, see run_checks
        -h|--help)  awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;;
        *) echo "Unknown option: $1 (see: bash scripts/build_env.sh --help)" >&2; exit 2 ;;
    esac
    shift
done

say()  { printf '\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33mWARNING:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }


# ============================================================================
# Checks: tools, Python packages and small smoke tests
# ============================================================================
# These must run INSIDE the environment, so `--check` re-runs this script
# through `conda run -n NAME ... --checks-in-env`, which lands here.
run_checks() {
    set +e   # keep going after a failed check; failures are counted instead
    local pass=0 fail=0 warnings=0

    ok()    { printf '  \033[32m✓\033[0m %-28s %s\n' "$1" "$2"; pass=$((pass + 1)); }
    bad()   { printf '  \033[31m✗\033[0m %-28s %s\n' "$1" "$2"; fail=$((fail + 1)); }
    meh()   { printf '  \033[33m!\033[0m %-28s %s\n' "$1" "$2"; warnings=$((warnings + 1)); }
    first() { head -n1 | tr -d '\r' | cut -c1-70; }

    echo "Environment: ${CONDA_PREFIX:-<none active>}"
    echo "Platform:    $(uname -s)/$(uname -m)"

    # --- Command-line tools -------------------------------------------------
    echo; echo "Command-line tools"
    tool() {  # name, version command, required (1) or optional (0)
        local name="$1" cmd="$2" req="${3:-1}" out
        if out="$(eval "$cmd" 2>&1)"; then ok "$name" "$(echo "$out" | first)"
        elif [[ "$req" == 1 ]]; then bad "$name" "not found or not working"
        else meh "$name" "not found (optional)"; fi
    }
    tool python     "python --version"
    tool snakemake  "snakemake --version"
    tool augur      "augur --version"
    tool nextclade  "nextclade --version"
    tool mafft      "mafft --version 2>&1 | grep -m1 -E 'v[0-9]'"
    tool iqtree     "(iqtree3 --version || iqtree2 --version || iqtree --version) 2>/dev/null | grep -m1 -i 'iq-tree'"
    tool seqkit     "seqkit version"
    tool blastn     "blastn -version"
    tool csvtk      "csvtk version"
    tool sqlite3    "python -c 'import sqlite3; print(\"sqlite\", sqlite3.sqlite_version)'"
    tool nextstrain "nextstrain --version" 0
    tool auspice    "auspice --version" 0

    # --- Python packages ----------------------------------------------------
    echo; echo "Python packages"
    python - <<'PY' || fail=$((fail + 1))
import importlib, sys
mods = [("pandas", "pandas"), ("Bio", "biopython"), ("treetime", "treetime"), ("yaml", "pyyaml"),
        ("matplotlib", "matplotlib"), ("altair", "altair"), ("vl_convert", "vl-convert-python"),
        ("marimo", "marimo"), ("itables", "itables"), ("pptx", "python-pptx"),
        ("openpyxl", "openpyxl"), ("PIL", "pillow")]
bad = 0
for mod, name in mods:
    try:
        m = importlib.import_module(mod)
        v = getattr(m, "__version__", "") or ""
        if not v:
            try:
                from importlib.metadata import version
                v = version(name)
            except Exception:
                v = ""
        print(f"  \033[32m✓\033[0m {name:<28} {v}")
    except Exception as e:
        print(f"  \033[31m✗\033[0m {name:<28} {type(e).__name__}: {e}")
        bad += 1
import pandas
if int(pandas.__version__.split(".")[0]) >= 3:
    print("  \033[31m✗\033[0m pandas < 3 required by augur 34")
    bad += 1
sys.exit(1 if bad else 0)
PY

    # --- Smoke tests on four tiny related HA sequences ----------------------
    echo; echo "Smoke tests"
    CHECK_TMP="$(mktemp -d "${TMPDIR:-/tmp}/pekosz-check.XXXXXX")"
    trap 'rm -rf "$CHECK_TMP"' EXIT
    write_test_data "$CHECK_TMP"

    smoke() {  # name, command (run inside the temporary test directory)
        local name="$1"; shift
        if (cd "$CHECK_TMP" && eval "$*") > "$CHECK_TMP/$name.log" 2>&1; then ok "$name" "passed"
        else bad "$name" "failed – last lines:"; tail -n 5 "$CHECK_TMP/$name.log" | sed 's/^/        /'; fi
    }
    smoke "augur filter (+seqkit)" \
        "augur filter --sequences seqs.fasta --metadata meta.tsv --query \"(coverage >= 0.9)\" --output-sequences f.fasta --output-metadata f.tsv --output-log flog.tsv && grep -q filter_by_query flog.tsv"
    smoke "augur align (mafft)" \
        "augur align --sequences seqs.fasta --output aln.fasta --nthreads 1"
    smoke "augur tree (iqtree)" \
        "augur tree --alignment aln.fasta --output tree.nwk --nthreads 1"
    local DB="$REPO/scripts/flusort/blast_database/pyflute_ha_database"
    if [[ -e "$DB.nsq" || -e "$DB.nal" ]]; then
        smoke "blastn (flusort database)" \
            "seqkit head -n 1 seqs.fasta > q.fasta && blastn -query q.fasta -db '$DB' -outfmt 6 -max_target_seqs 1 > hits.tsv && test -s hits.tsv"
    else
        meh "blastn (flusort database)" "database not found, skipped"
    fi
    smoke "report charts (vl-convert)" \
        "python -c \"import altair as alt, pandas as pd, vl_convert as v; c=alt.Chart(pd.DataFrame({'x':[1,2]})).mark_bar().encode(x='x:Q'); open('c.png','wb').write(v.vegalite_to_png(c.to_dict()))\""
    smoke "report deck (python-pptx)" \
        "python -c \"from pptx import Presentation; p=Presentation(); p.slides.add_slide(p.slide_layouts[6]); p.save('t.pptx')\""
    smoke "report script (parse)" \
        "python '$REPO/scripts/report.py' --help > /dev/null"
    smoke "snakemake (parse workflow)" \
        "cd '$REPO' && snakemake --list-rules > /dev/null"
    if [[ $NETWORK -eq 1 ]]; then
        smoke "nextclade dataset download" "nextclade dataset get -n flu_h3n2_ha -o ds && test -s ds/pathogen.json"
    fi

    # --- Summary ------------------------------------------------------------
    echo
    if [[ $fail -eq 0 ]]; then
        printf '\033[32mAll %d checks passed\033[0m' "$pass"
        if [[ $warnings -gt 0 ]]; then printf ' (%d optional item(s) missing)' "$warnings"; fi
        echo
        return 0
    else
        printf '\033[31m%d check(s) failed\033[0m, %d passed. See the messages above.\n' "$fail" "$pass"
        return 1
    fi
}

write_test_data() {  # dir: four related HA sequences (differing only near the 3' end) + metadata
    local dir="$1"
    local core="ATGAAGGCAATACTAGTAGTTCTGCTATATACATTTGCAACCGCAAATGCAGACACATTATGTATAGGTTATCATGCGAACAATTCAACAGACACTGTAGACACAGTACTAGAAAAGAATGTAACAGTAACACACTCTGTTAACCTTCTAGAAGACAAGCATAACGGGAAACTATGCAAACTAAGAGGGGTAGCCCCATTGCATTTGGGTAAATGTAACATTGCTGGCTGGATCCTGGGAAATCCAGAGTGTGAATCACTCTCCACAGCAAGCTCATGGTCCTACATTGTGGAAACATCTAGTTCAGACAATGGAACGTGTTACCCAGGAGATTTCATCGATTATGAGGAGCTAAGAGAGCAATTGAGCTCAGTGTCATCATTTGAAAGGTTTGAGATATTCCCCAAGACAAGTTCATGGCCCAATCATGACTCGAACAAAGGTGTAACGGCAGCATGTCCTCATGCTGGAGCAAAAAGCTTCTACAAAAATTTAATATGGCTAGTTAAAAAAGGAAATTCATACCCAAAGCTCAGCAAATCCTACATTAATGATAAAGGGAAAGAAGTCCTCGTGCTATGGGGCATTCACCATCCATCTACTAGTGCTGACCAACAAAGTCTCTATCAGAATGCAGATGCATATGTTTTTGTGGGGTCATCAAGATACAGCAAGAAGTTCAAGCCGGAAATAGCAATAAGACCCAAAGTGAGGGATCAAGAAGGGAGAATGAACTATTACTGGACACTAGTAGAGCCGGGAGACAAAATAACATTCGAAGCAACTGGAAATCTAGTGGTACCGAGATATGCATTCGCAATGGAAAGAAATGCTGGATCTGGTATTATCATTTCAGATACACCAGTCCACGATTGCAATACAACTTGTCAAACACCCAAGGGTGCTATAAACACCAGCCTCCCATTTCAGAATATACATCCGATCACAATTGGAAAATGTCCAAAATATGTAAAAAGCACAAAATTGAGACTGGCCACAGGATTGAGGAATATCCCGTCTATTCAATCTAGAGGCCTATTTGGGGCCATTGCCGGTTTCATTGAAGGGGGGTGGACAGGGATGGTAGATGGATGGTACGGTTATCACCATCAAAATGAGCAGGGGTCAGGATATGCAGCCGACCTGAAGAGCACACAGAATGCCATTGACGAGATTACTAACAAAGTAAATTCTGTTATTGAAAAGATGAATACACAGTTCACAGCAGTAGGTAAAGAGTTCAACCACCTGGAAAAAAGAATAGAGAATTTAAATAAAAAAGTTGATGATGGTTTCCTGGACATTTGGACTTACAATGCCGAACTGTTGGTTCTATTGGAAAATGAAAGAACTTTGGACTACCACGATTCAAATGTGAAGAACTTATATGAAAAGGTAAGAAGCCAGCTAAAAAACAATGCCAAGGAAATTGGAAACGGCTGCTTTGAATTTTACCACAAATGCGATAACACGTGCATGGAAAGTGTCAAAAATGGGACTTATGACTACCCAAAATACTCAGAGGAAGCAAAATTAAACAGAGAAGAAATAGATGGGGTAAAGCTGGAATCAACAAGGATTTACCAGATTTTGGCGATCTATTCAACTGTCGCCAGTTCATTGGTACTGGTAGTCTCCCTGGGGGCAATCAGTTTCTGGATGTGCTCTAATGGGTCTCTACAGTGTAGAATATGTAT"
    {
        printf '>A\n%sTTAA\n' "$core"
        printf '>B\n%sTTAG\n' "$core"
        printf '>C\n%sCTAA\n' "$core"
        printf '>D\n%sTTGA\n' "$core"
    } > "$dir/seqs.fasta"
    printf "strain\tdate\tcoverage\tqc_overallStatus\nA\t2024-01-01\t0.99\tgood\nB\t2024-02-01\t0.99\tgood\nC\t2024-03-01\t0.99\tmediocre\nD\t2024-04-01\t0.50\tbad\n" > "$dir/meta.tsv"
}

# Checks only, already inside the environment (re-entry from --check).
if [[ "$MODE" == "checks-in-env" ]]; then
    run_checks
    exit $?
fi


# ============================================================================
# --lock: regenerate the cross-platform lockfile (no conda environment needed)
# ============================================================================
# Pins exact versions for osx-arm64 (Apple Silicon), osx-64 (Intel Mac /
# Rosetta) and linux-64 (Linux and WSL2). Commit the result; others then get
# exactly the tested versions with --locked.
if [[ "$MODE" == "lock" ]]; then
    command -v conda-lock >/dev/null 2>&1 || die "conda-lock is not installed. Install it with
       'pipx install conda-lock' or 'mamba install -n base -c conda-forge conda-lock'."
    say "Locking $ENV_FILE for osx-arm64, osx-64 and linux-64"
    conda-lock lock \
        --file "$ENV_FILE" \
        --platform osx-arm64 --platform osx-64 --platform linux-64 \
        --lockfile "$LOCK_FILE"
    say "Wrote $LOCK_FILE. Test it with:  bash scripts/build_env.sh --locked"
    exit 0
fi


# ============================================================================
# Platform
# ============================================================================
OS="$(uname -s)"; ARCH="$(uname -m)"
PLATFORM="$OS/$ARCH"
if [[ "$OS" == "Linux" ]] && grep -qiE "microsoft|wsl" /proc/version 2>/dev/null; then
    PLATFORM="WSL/$ARCH"
    case "$PWD" in
        /mnt/[a-z]/*) warn "This repository is on the Windows drive ($PWD). Snakemake and
         conda are much slower there and file permissions can break the build.
         Clone the repository inside WSL instead, e.g.  cd ~ && git clone ..." ;;
    esac
fi
if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" && $INTEL -eq 1 ]]; then
    export CONDA_SUBDIR=osx-64
    PLATFORM="$PLATFORM (building osx-64 under Rosetta 2)"
    /usr/bin/pgrep -q oahd || warn "Rosetta 2 does not appear to be running. Install it with:
         softwareupdate --install-rosetta --agree-to-license"
fi
say "Platform: $PLATFORM"

# Data-protection git hooks (.githooks/ -> scripts/data_guard.sh): block commits
# and pushes containing GISAID or unpublished JHH data. Enabled for every clone.
if git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 \
   && [[ "$(git -C "$REPO" config --get core.hooksPath || true)" != ".githooks" ]]; then
    git -C "$REPO" config core.hooksPath .githooks
    say "Enabled the data-protection git hooks (git config core.hooksPath .githooks)"
fi

# Drag-and-drop folders for preparing the JHH input files (scripts/prepare_source.py).
# They hold private data, so git never tracks them; create them on every clone.
for dir in source_prep/runs source_prep/output; do
    if [[ ! -d "$REPO/$dir" ]]; then
        mkdir -p "$REPO/$dir"
        say "Created the empty folder $dir/ (drop sequencing-run FASTA files into source_prep/runs/)"
    fi
done


# ============================================================================
# Conda front end: mamba, then conda, then micromamba
# ============================================================================
if command -v mamba >/dev/null 2>&1; then
    CONDA=mamba
elif command -v conda >/dev/null 2>&1; then
    CONDA=conda
elif command -v micromamba >/dev/null 2>&1; then
    CONDA=micromamba
else
    die "conda was not found. Install Miniforge (https://conda-forge.org/download/), open a
       new terminal, and run this script again."
fi
say "Using $CONDA ($($CONDA --version 2>&1 | head -n1))"

if [[ "$CONDA" == "conda" ]]; then
    ver="$(conda --version | awk '{print $2}')"
    major="${ver%%.*}"; rest="${ver#*.}"; minor="${rest%%.*}"
    if (( major < 23 || (major == 23 && minor < 10) )); then
        warn "conda $ver is old and its solver is slow. Update first:  conda update -n base conda"
    fi
fi

# Strict channel priority for this process only (does not touch your .condarc)
export CONDA_CHANNEL_PRIORITY=strict

env_exists() { $CONDA env list 2>/dev/null | awk '{print $1}' | grep -qx "$NAME"; }
remove_env() { say "Removing existing environment '$NAME'"; $CONDA env remove -y -n "$NAME"; }


# ============================================================================
# Create / update the environment (skipped by --check)
# ============================================================================
create_from_lockfile() {
    [[ -f "$LOCK_FILE" ]] || die "$LOCK_FILE not found. Create it with:  bash scripts/build_env.sh --lock"
    if env_exists; then remove_env; fi
    say "Creating environment '$NAME' from $LOCK_FILE (exact versions)"
    if [[ "$CONDA" == "micromamba" ]]; then
        micromamba create -y -n "$NAME" -f "$LOCK_FILE" || die "Locked install failed."
    elif command -v conda-lock >/dev/null 2>&1; then
        conda-lock install -n "$NAME" "$LOCK_FILE" || die "Locked install failed."
    else
        die "Installing from the lockfile needs conda-lock (pipx install conda-lock) or micromamba."
    fi
}

create_or_update_from_env_file() {
    if env_exists; then
        say "Updating environment '$NAME' from $ENV_FILE"
        $CONDA env update -n "$NAME" -f "$ENV_FILE" --prune \
            || die "Update failed. Try a clean rebuild:  bash scripts/build_env.sh --recreate"
        return
    fi
    say "Creating environment '$NAME' from $ENV_FILE (this takes a few minutes)"
    if ! $CONDA env create -n "$NAME" -f "$ENV_FILE"; then
        if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" && $INTEL -eq 0 ]]; then
            die "The Apple Silicon build failed to solve. Retry with an Intel build that runs
       under Rosetta 2:  bash scripts/build_env.sh --intel"
        fi
        die "Environment creation failed (see the solver message above)."
    fi
}

# Pin the environment's own channel settings so later `conda install`s
# inside it stay on conda-forge/bioconda with strict priority.
write_env_condarc() {
    local prefix
    prefix="$($CONDA env list | awk -v n="$NAME" '$1==n {print $NF}')"
    [[ -n "$prefix" && -d "$prefix" ]] || return 0
    cat > "$prefix/.condarc" <<EOF
channels:
  - conda-forge
  - bioconda
channel_priority: strict
EOF
    if [[ -n "${CONDA_SUBDIR:-}" ]]; then echo "subdir: $CONDA_SUBDIR" >> "$prefix/.condarc"; fi
}

case "$MODE" in
    recreate) if env_exists; then remove_env; fi
              create_or_update_from_env_file; write_env_condarc ;;
    locked)   create_from_lockfile; write_env_condarc ;;
    build)    create_or_update_from_env_file; write_env_condarc ;;
    check)    ;;
esac


# ============================================================================
# Check the environment (re-runs this script inside it; see run_checks)
# ============================================================================
env_exists || die "Environment '$NAME' not found. Build it with:  bash scripts/build_env.sh"
say "Checking environment '$NAME'"
CHECK_ARGS=(--checks-in-env)
if [[ $NETWORK -eq 1 ]]; then CHECK_ARGS+=(--network); fi

# `conda run` buffers output unless told not to; micromamba (and mamba 2) stream it.
if [[ "$CONDA" != "micromamba" ]] && command -v conda >/dev/null 2>&1; then
    conda run -n "$NAME" --no-capture-output bash "$THIS_SCRIPT" "${CHECK_ARGS[@]}"
else
    $CONDA run -n "$NAME" bash "$THIS_SCRIPT" "${CHECK_ARGS[@]}"
fi

say "Done. Activate the environment with:  conda activate $NAME"
