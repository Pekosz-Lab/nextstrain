#!/usr/bin/env bash
# =============================================================================
# data_guard.sh: keep GISAID and unpublished JHH sequence data out of git.
#
# GISAID data may only live in source/ (and tutorial/vaccine.fasta). JHH
# sequences stay private until they are released on GISAID. This repository
# is public, so neither may ever be committed or pushed.
#
#   bash scripts/data_guard.sh            scan your copy of the repository for
#                                         GISAID data stored outside source/
#   bash scripts/data_guard.sh --staged   check files staged for commit   (.githooks/pre-commit)
#   bash scripts/data_guard.sh --push     check commits about to be pushed (.githooks/pre-push)
#   bash scripts/data_guard.sh --history  check every file ever committed (audit)
#
# GISAID data is recognised by any of:
#   - FASTA headers carrying GISAID accessions (EPI_ISL_..., EPI...) or
#     GISAID type labels (A_/_H3N2, B_/_Victoria)
#   - FASTA headers naming a strain or accession from a GISAID file in source/
#   - FASTA sequences identical to a sequence in a GISAID file in source/
#   - tables (.tsv .csv .txt .tab) listing EPI_ISL accessions (GISAID metadata)
#   - byte-identical copies of a GISAID file in source/
#
# Commits and pushes are also blocked for: anything under a source/ folder or
# in the JHH prep data (source_prep/runs/, source_prep/output/,
# source_prep/run_dates.csv),
# copies of source/ files, FASTAs sharing sequence IDs with the JHH data in
# source/, databases / archives / spreadsheets / slide decks, data files at
# the top level of the repository, new Jupyter notebooks and files > 10 MB.
#
# A maintainer who has confirmed that JHH sequences are already public (e.g.
# when regenerating the tutorial dataset) can allow the JHH check, and only
# that check, for one commit:   ALLOW_JHH_DATA=1 git commit ...
# The GISAID checks can never be switched off. Do not use --no-verify.
#
# Exit status: 0 = clean, 1 = problem found, 2 = usage error.
# Needs only bash, git, awk, grep and sort: works with or without conda and
# from any git client (terminal, Positron, VS Code, GitHub Desktop).
# =============================================================================
set -u
export LC_ALL=C

MODE="${1:---scan}"
case "$MODE" in
    --scan|--staged|--push|--history) ;;
    -h|--help) sed -n '2,37p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "data_guard: unknown option '$MODE' (try --help)" >&2; exit 2 ;;
esac
# Hooks: print to stderr so git GUIs show the message.
[ "$MODE" = "--scan" ] || exec 1>&2

root=$(git rev-parse --show-toplevel 2>/dev/null) \
    || { echo "data_guard: run this inside the nextstrain repository" >&2; exit 2; }
cd "$root" || exit 2
tmp=$(mktemp -d "${TMPDIR:-/tmp}/data_guard.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
: > "$tmp/violations"

MAX_MB=10
FASTA_EXT='\.(fasta|fa|fna|fas|ffn|aln|fasta\.txt)$'
TABLE_EXT='\.(tsv|csv|txt|tab)$'
ROOT_DATA_EXT='\.(fasta|fa|fna|fas|tsv|csv|txt|xls|xlsx)$'
CONTAINER_EXT='\.(db|sqlite|sqlite3|tar|tgz|gz|zip|xz|bz2|7z|xls|xlsx|pptx)$'
GISAID_HDR='EPI_ISL_[0-9]+|(^|[|[:space:]>])EPI[0-9]{5,}|A_/_H[0-9]|B_/_(Victoria|Yamagata)'

# --- small helpers ------------------------------------------------------------
flag() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$tmp/violations"; }   # category, path, reason
count() { grep -c "$@" 2>/dev/null || true; }

is_fasta() {    # $1 = path (for the extension), $2 = file with the content
    printf '%s\n' "$1" | grep -qiE "$FASTA_EXT" && return 0
    [ "$(head -c 4096 "$2" | tr -d '\000' | awk 'NF { print substr($1, 1, 1); exit }')" = ">" ]
}
fasta_ids() {   # first word of each header, as the pipeline reads it
    grep '^>' | tr -d '\r' | sed 's/^>//; s/[|[:space:]].*//' | sort -u
}
strain_names() {    # header fields that name a strain (contain "/") or a GISAID accession
    grep '^>' | tr -d '\r' | sed 's/^>//' | awk -F'|' '{
        split($1, w, " "); print w[1]
        for (i = 1; i <= NF; i++) { f = $i; gsub(/^[ \t]+|[ \t]+$/, "", f)
                                    if (f ~ /\// || f ~ /^EPI/) print f } }' | sort -u
}
sequences() {   # one upper-case, gap-free sequence per record (records >= 200 nt only)
    tr -d '\r' | awk 'function out() { if (length(s) >= 200) print s; s = "" }
                      /^>/ { out(); next } { gsub(/[^A-Za-z]/, ""); s = s toupper($0) }
                      END  { out() }' | sort -u
}
gisaid_seq_hits() {     # $1 = FASTA; counts records whose sequence is identical to a
                        # GISAID sequence, skipping JHH records (a JHH segment can be
                        # identical to a vaccine strain's and is still the lab's own data)
    tr -d '\r' < "$1" | awk -v G="$tmp/gisaid_seqs" -v J="$tmp/jhh_ids" '
        function key(x) { sub(/[| \t].*/, "", x); sub(/_[0-9]+$/, "", x); return x }
        function out() { if (id != "" && length(s) >= 200 && (s in g) && !(key(id) in j)) n++; s = "" }
        BEGIN { while ((getline l < G) > 0) g[l] = 1; while ((getline l < J) > 0) j[key(l)] = 1 }
        /^>/  { out(); id = substr($0, 2); next }
              { gsub(/[^A-Za-z]/, ""); s = s toupper($0) }
        END   { out(); print n + 0 }'
}

# --- reference data: what is in source/ (and tutorial/vaccine.fasta) ------------
# GISAID files are recognised by their headers; every other FASTA in source/ is
# treated as JHH data.
: > "$tmp/src_hash"; : > "$tmp/gisaid_hash"; : > "$tmp/gisaid_names"
: > "$tmp/gisaid_seqs"; : > "$tmp/jhh_ids"; : > "$tmp/gisaid_sources"
while IFS= read -r f; do
    [ -f "$f" ] || continue
    h=$(git hash-object "$f"); echo "$h" >> "$tmp/src_hash"
    is_fasta "$f" "$f" || continue
    if grep '^>' "$f" | grep -qE "$GISAID_HDR"; then
        echo "$h" >> "$tmp/gisaid_hash"; echo "$f" >> "$tmp/gisaid_sources"
        strain_names < "$f" >> "$tmp/gisaid_names"
        sequences    < "$f" >> "$tmp/gisaid_seqs"
    else
        fasta_ids < "$f" >> "$tmp/jhh_ids"
    fi
done < <(find source -type f ! -name '.DS_Store' 2>/dev/null; echo tutorial/vaccine.fasta)
for f in gisaid_names gisaid_seqs jhh_ids; do sort -u -o "$tmp/$f" "$tmp/$f"; done

# Public Nextclade datasets that fetch_hana_datasets (segments.smk) downloads
# from Nextstrain into nextclade/flu/. Nextstrain publishes these openly; some
# reference headers carry the EPI_ISL accession of the reference strain.
# Only these exact file names are exempt from the GISAID checks.
public_dataset() {
    case "$1" in nextclade/flu/*/*/reference.fasta|nextclade/flu/*/*/sequences.fasta) return 0 ;; esac
    return 1
}

# --- content checks for one file --------------------------------------------------
# $1 = path in the repository, $2 = file holding the content, $3 = 1 to run the
# JHH check, $4 = path shown to the user (defaults to $1)
check_content() {
    local f="$1" c="$2" jhh="$3" p="${4:-$1}" h n total
    public_dataset "$f" && return
    h=$(git hash-object "$c")
    if grep -qx "$h" "$tmp/gisaid_hash"; then
        flag GISAID "$p" "exact copy of a GISAID file in source/"; return
    fi
    if grep -qx "$h" "$tmp/src_hash"; then
        flag DATA "$p" "exact copy of a file in source/"; return
    fi
    if is_fasta "$f" "$c"; then
        if grep '^>' "$c" | grep -qE "$GISAID_HDR"; then
            flag GISAID "$p" "FASTA headers carry GISAID accessions (EPI_ISL_/EPI) or GISAID type labels"; return
        fi
        if [ -s "$tmp/gisaid_names" ]; then
            strain_names < "$c" > "$tmp/names"
            n=$(count -Fx -f "$tmp/gisaid_names" "$tmp/names")
            if [ "$n" -gt 0 ]; then
                flag GISAID "$p" "$n strain names/accessions match the GISAID file(s) in source/"; return
            fi
        fi
        if [ -s "$tmp/gisaid_seqs" ]; then
            n=$(gisaid_seq_hits "$c")
            if [ "$n" -gt 0 ]; then
                flag GISAID "$p" "$n sequences are identical to sequences in the GISAID file(s) in source/"; return
            fi
        fi
        if [ "$jhh" = 1 ] && [ -s "$tmp/jhh_ids" ]; then
            fasta_ids < "$c" > "$tmp/ids"
            n=$(count -Fx -f "$tmp/jhh_ids" "$tmp/ids"); total=$(wc -l < "$tmp/ids" | tr -d ' ')
            [ "$n" -gt 0 ] && flag JHH "$p" "shares $n of $total sequence IDs with the JHH data in source/"
        fi
    elif printf '%s\n' "$f" | grep -qiE "$TABLE_EXT" && grep -qE 'EPI_ISL_[0-9]+' "$c"; then
        flag GISAID "$p" "table lists GISAID accessions (EPI_ISL_...): GISAID metadata"
    fi
}

# --- checks on a committed or staged file -----------------------------------------
# $1 = path in the repository, $2 = git object (":path" or "commit:path"),
# $3 = path shown to the user, $4 = 1 if the file is newly added
check_git_file() {
    local f="$1" obj="$2" shown="$3" added="$4" size
    case "/$f" in */source/*|*/source_prep/runs/*|*/source_prep/output/*|*/source_prep/run_dates.csv)
        flag DATA "$shown" "inside source/ or the source_prep/ data folders (raw JHH/GISAID data)"; return ;;
    esac
    if printf '%s\n' "$f" | grep -qiE "$CONTAINER_EXT"; then
        flag DATA "$shown" "databases, archives, spreadsheets and slide decks can hold sequence data and are never tracked"; return
    fi
    case "$f" in */*) ;; *)
        printf '%s\n' "$f" | grep -qiE "$ROOT_DATA_EXT" \
            && flag DATA "$shown" "data file at the top level of the repository (data belongs in source/, outputs in results/)" ;;
    esac
    case "$f" in *.ipynb) [ "$added" = 1 ] \
        && flag POLICY "$shown" "new Jupyter notebook: use marimo (.py) or Quarto (.qmd); notebook outputs can embed data" ;;
    esac
    size=$(git cat-file -s "$obj" 2>/dev/null || echo 0)
    case "$f" in nextclade/flu/*) size=0 ;; esac    # public Nextclade datasets (tree.json is ~10 MB)
    [ "$size" -gt $((MAX_MB * 1024 * 1024)) ] \
        && flag POLICY "$shown" "larger than ${MAX_MB} MB ($((size / 1024 / 1024)) MB); large files are almost always data"
    git cat-file -p "$obj" > "$tmp/blob" 2>/dev/null || return
    check_content "$f" "$tmp/blob" 1 "$shown"
}

# --- collect the files to check ------------------------------------------------------
case "$MODE" in
--staged)
    git diff --cached --name-only --diff-filter=A -z > "$tmp/added"
    while IFS= read -r -d '' f; do
        added=0; tr '\0' '\n' < "$tmp/added" | grep -qxF -- "$f" && added=1
        check_git_file "$f" ":$f" "$f" "$added"
    done < <(git diff --cached --name-only --diff-filter=ACMR -z)
    ;;
--push)
    # git passes "<local ref> <local sha> <remote ref> <remote sha>" lines on stdin;
    # check every commit that the remote does not have yet.
    while read -r _lref lsha _rref rsha; do
        case "$lsha" in *[!0]*) ;; *) continue ;; esac              # branch deletion
        case "$rsha" in
            *[!0]*) git rev-list "$rsha..$lsha" 2>/dev/null \
                        || git rev-list "$lsha" --not --remotes ;;      # remote sha unknown here
            *)      git rev-list "$lsha" --not --remotes ;;          # new branch
        esac
    done > "$tmp/commits"
    : > "$tmp/seen"
    while read -r c; do
        while IFS= read -r -d '' f; do
            blob=$(git rev-parse "$c:$f" 2>/dev/null) || continue
            grep -qx "$blob" "$tmp/seen" && continue
            echo "$blob" >> "$tmp/seen"
            check_git_file "$f" "$c:$f" "$f  (in commit ${c:0:8})" 0
        done < <(git diff-tree --root --no-commit-id -r -z --name-only --diff-filter=ACMR "$c")
    done < <(sort -u "$tmp/commits")
    ;;
--history)
    # Every file version ever committed on any branch. To stay fast, only files
    # whose path, type or size can matter are opened (FASTA, tables, source/,
    # containers, top-level data, files over the size limit).
    tab=$(printf '\t')
    git rev-list --all --objects \
      | git cat-file --batch-check="%(objecttype)$tab%(objectname)$tab%(objectsize)$tab%(rest)" \
      | FX="$FASTA_EXT" TX="$TABLE_EXT" CX="$CONTAINER_EXT" RX="$ROOT_DATA_EXT" \
        awk -F'\t' -v max=$((MAX_MB * 1024 * 1024)) '
            $1 != "blob" || $4 == "" { next }
            { p = tolower($4) }
            p ~ /(^|\/)source\// || p ~ ENVIRON["FX"] || p ~ ENVIRON["TX"] || p ~ ENVIRON["CX"] ||
            (p !~ /\// && p ~ ENVIRON["RX"]) || $3 > max {
                print $2 "\t" $4 }' > "$tmp/candidates"
    while IFS="$tab" read -r blob f; do
        check_git_file "$f" "$blob" "$f  (in history; see: git log --all -- '$f')" 0
    done < "$tmp/candidates"
    ;;
--scan)
    # Everything on disk except the places GISAID data is allowed to be:
    # source/, tutorial/vaccine.fasta, the git-ignored JHH prep folders
    # (source_prep/runs/, source_prep/output/) and the git-ignored pipeline folders
    # (data/, results/, auspice/, reports/, snapshots/, .run/, fludb.db).
    while IFS= read -r -d '' f; do
        f="${f#./}"
        [ "$f" = "tutorial/vaccine.fasta" ] && continue
        case "$f" in */*) ;; *)
            printf '%s\n' "$f" | grep -qiE "$ROOT_DATA_EXT" \
                && flag DATA "$f" "data file at the top level of the repository (data belongs in source/, outputs in results/)" ;;
        esac
        check_content "$f" "$f" 0
    done < <(find . \( -path ./.git -o -path ./.snakemake -o -path ./source -o -path ./data \
                       -o -path ./source_prep/runs -o -path ./source_prep/output \
                       -o -path ./results -o -path ./auspice -o -path ./reports \
                       -o -path ./snapshots -o -path ./.run \) -prune \
                    -o -type f ! -name '.DS_Store' ! -name 'fludb.db' -print0)
    ;;
esac

# --- report ---------------------------------------------------------------------------
if [ ! -s "$tmp/violations" ]; then
    case "$MODE" in
        --scan)    echo "data_guard: OK, no GISAID data found outside source/." ;;
        --history) echo "data_guard: OK, no protected data found in the git history." ;;
    esac
    exit 0
fi

list() {    # print the violations of one category with their full path on this computer
    awk -F'\t' -v cat="$1" -v root="$root" \
        '$1 == cat && !seen[$2]++ { printf "    %s/%s\n        -> %s\n", root, $2, $3 }' "$tmp/violations"
}
line="==============================================================================="

if grep -q '^GISAID' "$tmp/violations"; then
    cat <<EOF

$line
  STOP: GISAID TERMS OF USE VIOLATION
$line
GISAID sequence data was found outside source/.

GISAID's Database Access Agreement forbids sharing GISAID data with anyone
who has not signed it. This repository is PUBLIC on GitHub: anything pushed
to it is published to the world and stays in its history even after deletion.
Publishing these files would breach the agreement you and the lab signed and
can cost the lab its GISAID access.

Out-of-compliance files on this computer:
EOF
    list GISAID
fi
if grep -q '^JHH' "$tmp/violations"; then
    cat <<EOF

$line
  STOP: UNPUBLISHED JHH SEQUENCE DATA
$line
JHH sequences are private until the Mostafa Lab releases them on GISAID.
Files on this computer containing them:
EOF
    list JHH
fi
if grep -q '^DATA' "$tmp/violations"; then
    printf '\n%s\n  STOP: DATA FILES THAT MUST NOT BE COMMITTED\n%s\n' "$line" "$line"
    list DATA
fi
if grep -q '^POLICY' "$tmp/violations"; then
    printf '\n%s\n  BLOCKED BY REPOSITORY POLICY (see the wiki: Best Practices)\n%s\n' "$line" "$line"
    list POLICY
fi

# A maintainer may allow the JHH check alone (e.g. tutorial data already public).
if [ "${ALLOW_JHH_DATA:-0}" = 1 ] && [ "$MODE" != "--scan" ] \
   && ! grep -qv '^JHH' "$tmp/violations"; then
    echo
    echo "ALLOW_JHH_DATA=1: JHH check overridden by a maintainer. Continuing."
    exit 0
fi

echo
echo "What to do now:"
case "$MODE" in
--staged)
    cat <<EOF
  1. Take the file(s) out of this commit (your files are not deleted):
         git restore --staged <file>
  2. Move GISAID or JHH data back into source/ (JHH run files: source_prep/runs/),
     or delete the stray copy. Pipeline outputs belong in results/.
  3. Commit again. Nothing has left your computer yet.
EOF
    ;;
--push)
    cat <<EOF
  The files are already inside commits on this computer, but nothing has
  been sent to GitHub. Do not push, and do not try to fix this with a new
  commit (the data stays in the earlier commit).
  1. Ask the repository maintainer to help remove the commit(s) listed above,
     or, if you know how: git reset --soft origin/main, unstage the files
     (git restore --staged <file>) and commit again.
  2. Move GISAID or JHH data back into source/ or delete the stray copy.
EOF
    ;;
--history)
    cat <<EOF
  These files are in the git history. If that history has been pushed to
  GitHub, tell the repository maintainer and Dr. Pekosz today: the history
  must be rewritten and GitHub asked to purge cached copies.
EOF
    ;;
--scan)
    cat <<EOF
  These files are not in git yet, but stored outside source/ they can be
  committed, synced or attached to an email by mistake. Move GISAID data
  into source/ (the only folder where it may live) or delete the copy.
EOF
    ;;
esac
echo "Do NOT bypass this check (git commit --no-verify). Questions: ask the repository maintainer."
echo
exit 1
