#!/usr/bin/env python3
"""
Build a static run report from the files Snakemake writes under .run/.

    python scripts/run_report.py                      # latest run
    python scripts/run_report.py --run-id 20261006T191100
    python scripts/run_report.py --all                # rebuild every run's report

Reads
    .run/run_logs/{RUN_ID}_provenance.txt              host, git commit, tool versions
    .run/run_logs/{RUN_ID}_snakemake_{SUCCESS,FAILED}.log
                                                       job start/finish times, failures
    .run/benchmarks/{rule}/{target}.tsv                runtime, memory, CPU per job
    .run/logs/{rule}/{target}.log                      per-job stdout + stderr

Writes
    .run/reports/{RUN_ID}/report.md                    summary document
    .run/reports/{RUN_ID}/figures/*.png                static figures
    .run/reports/{RUN_ID}/tables/*.tsv                 the numbers behind the figures
    .run/reports/index.md                              history of all runs

Every number is tied to a run: job times come from that run's main Snakemake
log, and a benchmark/log file is only attributed to the run if that run
actually executed the job and no later run re-executed it (benchmarks and job
logs are overwritten each time a job reruns).

This is separate from Snakemake's native `--report` output and from the
sequence-data reports built by scripts/build-reports.py (reports/).
"""

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

# ---------------------------------------------------------------------------
# Style. Subtype colours are fixed (never cycled) so they mean the same thing
# in every figure and every run.
# ---------------------------------------------------------------------------
SUBTYPE_COLORS = {"h3n2": "#2a78d6", "h1n1": "#eb6834", "vic": "#1baf7a"}
OTHER_COLOR = "#a8a7a2"   # ingest / non-subtype jobs
BAR_COLOR = "#2a78d6"
STATUS_COLORS = {"SUCCESS": "#008300", "FAILED": "#e34948", "UNKNOWN": "#a8a7a2"}
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SUBTYPES = ["h3n2", "h1n1", "vic"]
SEGMENTS = ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns", "genome"]

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "font.size": 9,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "legend.frameon": False,
})

TS_RE = re.compile(r"^\[(\w{3} \w{3}\s+\d+ \d\d:\d\d:\d\d \d{4})\]\s*$")
JOB_MSG_RE = re.compile(r"^Job (\d+): (.*)$")
RULE_RE = re.compile(r"^(?:local)?(?:rule|checkpoint) (\S+):\s*$")
JOBID_RE = re.compile(r"^\s+jobid: (\d+)\s*$")
EXEC_LOG_RE = re.compile(r"exec\s*>\s*(\S+)\s+2>&1")
LOG_RE = re.compile(r"^\s+log: (\S+?)(?:,|\s|$)")
WILDCARDS_RE = re.compile(r"^\s+wildcards: (.*)$")
FINISHED_RE = re.compile(r"^Finished jobid: (\d+) \(Rule: (\S+)\)")
ERROR_RE = re.compile(r"^Error in rule (\S+):\s*$")
CORES_RE = re.compile(r"^Provided cores: (\d+)")
TOTAL_RE = re.compile(r"^total\s+(\d+)\s*$")
WARN_RE = re.compile(r"\bwarn(ing)?s?\b", re.I)
ERR_RE = re.compile(r"\berror\b|traceback|exception", re.I)


def parse_ts(text):
    return dt.datetime.strptime(" ".join(text.split()), "%a %b %d %H:%M:%S %Y")


def fmt_dur(seconds):
    if seconds is None or pd.isna(seconds):
        return "–"
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def target_of(log_path):
    """`.run/logs/align/h3n2_ha.log` (or legacy `logs/align/...`) -> ('align', 'h3n2_ha')."""
    p = Path(log_path)
    return p.parent.name, p.stem


def split_target(target):
    """'h3n2_ha' -> ('h3n2', 'ha'); 'h3n2' -> ('h3n2', 'genome'); 'flusort' -> (None, None)."""
    parts = target.split("_")
    subtype = parts[0] if parts[0] in SUBTYPES else None
    if subtype is None:
        return None, None
    segment = parts[1] if len(parts) > 1 and parts[1] in SEGMENTS else "genome"
    return subtype, segment


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def parse_provenance(path):
    info, git_dirty, tools = {}, [], {}
    if not path or not path.exists():
        return info, git_dirty, tools
    section = None
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("== "):
            section = line.strip("= ").strip()
            continue
        if not line.strip():
            continue
        if section == "git":
            if re.fullmatch(r"[0-9a-f]{40}", line.strip()):
                info["git_commit"] = line.strip()
            elif line.startswith("not a git"):
                info["git_commit"] = line.strip()
            else:
                git_dirty.append(line.rstrip())
            continue
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if section == "tool versions" and key not in ("finished_utc", "status"):
            tools[key] = val
        else:
            info[key] = val
    return info, git_dirty, tools


def parse_main_log(path):
    """Return (jobs DataFrame, meta dict) from a Snakemake main log."""
    meta = {"cores": None, "planned": None, "first_ts": None, "last_ts": None,
            "nothing_to_do": False}
    jobs = {}
    if not path or not path.exists():
        return pd.DataFrame(), meta

    last_ts = None
    cur = None            # jobid of the block being read
    pending_rule = None   # rule header seen, jobid not yet seen
    error_rule = None     # inside an "Error in rule" block
    in_stats = False

    def job(jid):
        return jobs.setdefault(jid, {"jobid": jid, "rule": None, "message": None,
                                     "start": None, "end": None, "status": "running",
                                     "log": None, "wildcards": None})

    for raw in path.read_text(errors="replace").splitlines():
        line = raw.rstrip("\n")
        m = TS_RE.match(line)
        if m:
            last_ts = parse_ts(m.group(1))
            meta["first_ts"] = meta["first_ts"] or last_ts
            meta["last_ts"] = last_ts
            cur, pending_rule, error_rule = None, None, None
            continue
        if line.startswith("Job stats:"):
            in_stats = True
            continue
        if in_stats:
            m = TOTAL_RE.match(line)
            if m:
                meta["planned"] = int(m.group(1))
                in_stats = False
            continue
        m = CORES_RE.match(line)
        if m:
            meta["cores"] = int(m.group(1))
            continue
        if line.startswith("Nothing to be done"):
            meta["nothing_to_do"] = True
            continue
        m = JOB_MSG_RE.match(line)
        if m:
            cur = int(m.group(1))
            j = job(cur)
            j["message"], j["start"] = m.group(2), last_ts
            continue
        m = ERROR_RE.match(line)
        if m:
            error_rule, cur, pending_rule = m.group(1), None, None
            continue
        m = RULE_RE.match(line)
        if m:
            pending_rule, cur = m.group(1), None
            continue
        m = JOBID_RE.match(line)
        if m:
            jid = int(m.group(1))
            if error_rule:
                j = job(jid)
                j["rule"], j["status"], j["end"] = error_rule, "failed", last_ts
                cur = jid
            elif pending_rule:
                j = job(jid)
                j["rule"], j["start"] = pending_rule, j["start"] or last_ts
                cur, pending_rule = jid, None
            continue
        m = FINISHED_RE.match(line)
        if m:
            j = job(int(m.group(1)))
            j["rule"], j["end"], j["status"] = m.group(2), last_ts, "finished"
            continue
        if cur is not None:
            m = EXEC_LOG_RE.search(line) or LOG_RE.match(line)
            if m and not jobs[cur]["log"]:
                jobs[cur]["log"] = m.group(1)
                continue
            m = WILDCARDS_RE.match(line)
            if m:
                jobs[cur]["wildcards"] = m.group(1)

    df = pd.DataFrame(jobs.values())
    if df.empty:
        return df, meta
    df = df[df["rule"].notna() | df["start"].notna()].copy()
    df["rule"] = df["rule"].fillna("unknown")
    df["target"] = [target_of(p)[1] if isinstance(p, str) else r
                    for p, r in zip(df["log"], df["rule"])]
    df["key"] = df["rule"] + "/" + df["target"]
    df["wall_s"] = (df["end"] - df["start"]).dt.total_seconds()
    st = [split_target(t) for t in df["target"]]
    df["subtype"] = [s for s, _ in st]
    df["segment"] = [g for _, g in st]
    return df.sort_values("start", na_position="last").reset_index(drop=True), meta


def read_benchmarks(bench_dir):
    rows = []
    for f in sorted(bench_dir.glob("*/*.tsv")):
        try:
            b = pd.read_csv(f, sep="\t")
        except Exception:
            continue
        if b.empty:
            continue
        row = b.select_dtypes("number").mean().to_dict()   # mean over --benchmark-repeats
        row.update(rule=f.parent.name, target=f.stem, bench_file=str(f),
                   bench_mtime=dt.datetime.fromtimestamp(f.stat().st_mtime))
        rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["key"] = df["rule"] + "/" + df["target"]
    return df


def scan_logs(log_dir):
    rows = []
    for f in sorted(log_dir.glob("*/*.log")):
        try:
            text = f.read_text(errors="replace")
        except Exception:
            continue
        lines = text.splitlines()
        rows.append({
            "rule": f.parent.name, "target": f.stem, "key": f"{f.parent.name}/{f.stem}",
            "log_file": str(f), "lines": len(lines), "bytes": f.stat().st_size,
            "warning_lines": sum(bool(WARN_RE.search(l)) for l in lines),
            "error_lines": sum(bool(ERR_RE.search(l)) for l in lines),
            "log_mtime": dt.datetime.fromtimestamp(f.stat().st_mtime),
        })
    return pd.DataFrame(rows)


def discover_runs(run_log_dir):
    runs = {}
    for f in run_log_dir.glob("*_provenance.txt"):
        runs.setdefault(f.name.split("_")[0], {})["provenance"] = f
    for f in run_log_dir.glob("*_snakemake_*.log"):
        rid, status = f.name.split("_")[0], f.stem.rsplit("_", 1)[-1]
        runs.setdefault(rid, {})["main_log"] = f
        runs[rid]["status"] = status
    for rid in runs:
        runs[rid].setdefault("status", "UNKNOWN")
    return dict(sorted(runs.items()))


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def color_for(subtype):
    return SUBTYPE_COLORS.get(subtype, OTHER_COLOR)


def subtype_legend(ax, include_other=True, **kw):
    handles = [Patch(color=c, label=s) for s, c in SUBTYPE_COLORS.items()]
    if include_other:
        handles.append(Patch(color=OTHER_COLOR, label="ingest / other"))
    ax.legend(handles=handles, **kw)


def fig_timeline(jobs, out, run_id):
    j = jobs.dropna(subset=["start"]).copy()
    if j.empty:
        return None
    t0 = j["start"].min()
    j["end"] = j["end"].fillna(j["end"].max() if j["end"].notna().any() else j["start"].max())
    j["x0"] = (j["start"] - t0).dt.total_seconds() / 60
    j["x1"] = (j["end"] - t0).dt.total_seconds() / 60
    # Greedy lane packing so concurrent jobs sit on separate rows.
    lanes, lane_of = [], []
    for x0, x1 in zip(j["x0"], j["x1"]):
        for i, free_at in enumerate(lanes):
            if free_at <= x0:
                lanes[i] = max(x1, x0 + 1e-3)
                lane_of.append(i)
                break
        else:
            lanes.append(max(x1, x0 + 1e-3))
            lane_of.append(len(lanes) - 1)
    j["lane"] = lane_of

    # Concurrency curve
    events = sorted([(x, 1) for x in j["x0"]] + [(x, -1) for x in j["x1"]],
                    key=lambda e: (e[0], e[1]))
    xs, ys, n = [0.0], [0], 0
    for x, d in events:
        xs.append(x); ys.append(n)
        n += d
        xs.append(x); ys.append(n)

    height = 2.0 + min(len(lanes), 40) * 0.12
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(10, height + 1.6), sharex=True,
                                   gridspec_kw={"height_ratios": [1.2, height]})
    ax0.fill_between(xs, ys, step=None, color=BAR_COLOR, alpha=0.25, linewidth=0)
    ax0.plot(xs, ys, color=BAR_COLOR, linewidth=1.5)
    ax0.set_ylabel("jobs running")
    ax0.set_title(f"Job timeline — run {run_id}")
    ax0.set_ylim(bottom=0)

    for _, r in j.iterrows():
        width = max(r["x1"] - r["x0"], 0.02)
        edge = "#e34948" if r["status"] == "failed" else "white"
        ax1.barh(r["lane"], width, left=r["x0"], height=0.8,
                 color=color_for(r["subtype"]), edgecolor=edge, linewidth=0.6)
    ax1.set_yticks([])
    ax1.invert_yaxis()
    ax1.grid(axis="y", visible=False)
    ax1.set_xlabel(f"minutes since first job ({t0:%Y-%m-%d %H:%M:%S} host clock)")
    ax1.set_ylabel("concurrent job slots")
    subtype_legend(ax1, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8)
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_runtime_by_rule(rules, out):
    r = rules.dropna(subset=["total_s"]).sort_values("total_s")
    if r.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 0.28 * len(r) + 1.2))
    ax.barh(r["rule"], r["total_s"] / 60, color=BAR_COLOR, height=0.7)
    for y, (tot, n) in enumerate(zip(r["total_s"], r["jobs"])):
        ax.text(tot / 60, y, f"  {fmt_dur(tot)} · {int(n)} job{'s' if n != 1 else ''}",
                va="center", fontsize=7.5, color=INK_2)
    ax.set_xlabel("summed job runtime (minutes, from benchmarks)")
    ax.set_title("Where the time goes — runtime by rule")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, r["total_s"].max() / 60 * 1.35)
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_runtime_matrix(jobs, out):
    j = jobs.dropna(subset=["subtype", "s"])
    if j.empty:
        return None
    m = (j.groupby(["subtype", "segment"])["s"].sum() / 60).unstack("segment")
    m = m.reindex(index=[s for s in SUBTYPES if s in m.index],
                  columns=[s for s in SEGMENTS if s in m.columns])
    fig, ax = plt.subplots(figsize=(1.0 + 0.85 * m.shape[1], 1.0 + 0.6 * m.shape[0]))
    im = ax.imshow(m.values, cmap="Blues", aspect="auto", vmin=0)
    ax.set_xticks(range(m.shape[1]), m.columns)
    ax.set_yticks(range(m.shape[0]), m.index)
    ax.grid(False)
    vmax = pd.Series(m.values.ravel()).max()
    for (i, k), v in pd.DataFrame(m.values).stack().items():
        ax.text(k, i, f"{v:.1f}", ha="center", va="center", fontsize=8,
                color="white" if v > 0.6 * vmax else INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("minutes", color=INK_2)
    cb.outline.set_visible(False)
    ax.set_title("Summed runtime per build (all rules)")
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_memory(jobs, out):
    j = jobs.dropna(subset=["max_rss"])
    if j.empty:
        return None
    order = j.groupby("rule")["max_rss"].max().sort_values().index.tolist()
    pos = {r: i for i, r in enumerate(order)}
    fig, ax = plt.subplots(figsize=(8, 0.28 * len(order) + 1.2))
    for st in SUBTYPES + [None]:
        sub = j[j["subtype"] == st] if st else j[j["subtype"].isna()]
        if sub.empty:
            continue
        # small deterministic vertical offset per subtype so dots don't hide each other
        off = {"h3n2": -0.2, "h1n1": 0.0, "vic": 0.2}.get(st, 0.0)
        ax.scatter(sub["max_rss"], [pos[r] + off for r in sub["rule"]], s=18,
                   color=color_for(st), edgecolor="white", linewidth=0.6, zorder=3)
    ax.set_yticks(range(len(order)), order)
    ax.set_xlabel("peak resident memory per job (MB, max_rss)")
    ax.set_title("Peak memory by rule")
    ax.grid(axis="y", visible=False)
    subtype_legend(ax, loc="lower right", fontsize=8)
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_history(history, out):
    h = history.dropna(subset=["wall_s"])
    if len(h) < 2:
        return None
    fig, ax = plt.subplots(figsize=(max(5, 0.5 * len(h) + 2), 3.2))
    x = range(len(h))
    ax.bar(x, h["wall_s"] / 60, color=[STATUS_COLORS.get(s, OTHER_COLOR) for s in h["status"]],
           width=0.7)
    for i, (w, n, s) in enumerate(zip(h["wall_s"], h["executed"], h["status"])):
        ax.text(i, w / 60, f"{n} jobs\n{s.lower()}", ha="center", va="bottom", fontsize=7,
                color=INK_2)
    ax.set_xticks(list(x), [r[:8] + "\n" + r[9:] for r in h["run_id"]], fontsize=7)
    ax.set_ylabel("wall clock (minutes)")
    ax.set_title("Run history")
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, (h["wall_s"] / 60).max() * 1.3)
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def md_table(df, cols, headers=None, fmt=None):
    fmt = fmt or {}
    headers = headers or cols
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if c in fmt:
                v = fmt[c](v)
            elif v is None or (isinstance(v, float) and pd.isna(v)):
                v = "–"
            cells.append(str(v).replace("|", "\\|"))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def kv_table(pairs):
    out = ["| | |", "|---|---|"]
    out += [f"| **{k}** | {str(v).replace('|', '/')} |" for k, v in pairs]
    return "\n".join(out)


def run_summary(run_id, run, later_keys):
    """Collect everything known about one run. later_keys: jobs re-executed by later runs."""
    info, dirty, tools = parse_provenance(run.get("provenance"))
    jobs, meta = parse_main_log(run.get("main_log"))
    status = info.get("status") or run.get("status", "UNKNOWN")
    wall = None
    if meta["first_ts"] and meta["last_ts"]:
        wall = (meta["last_ts"] - meta["first_ts"]).total_seconds()
    if not jobs.empty:
        jobs["superseded"] = jobs["key"].isin(later_keys)
    return dict(run_id=run_id, info=info, dirty=dirty, tools=tools, jobs=jobs, meta=meta,
                status=status, wall_s=wall,
                executed=0 if jobs.empty else int(len(jobs)))


def build_report(run_id, runs, run_dir, quiet=False):
    ids = list(runs)
    later_keys = set()
    for rid in ids[ids.index(run_id) + 1:]:
        j, _ = parse_main_log(runs[rid].get("main_log"))
        if not j.empty:
            later_keys |= set(j["key"])

    S = run_summary(run_id, runs[run_id], later_keys)
    info, jobs, meta = S["info"], S["jobs"], S["meta"]

    out_dir = run_dir / "reports" / run_id
    fig_dir, tab_dir = out_dir / "figures", out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    bench = read_benchmarks(run_dir / "benchmarks")
    logs = scan_logs(run_dir / "logs")

    # Attribute benchmark + log files to this run only if this run executed the
    # job and no later run overwrote them.
    if not jobs.empty:
        attributable = jobs[~jobs["superseded"]]
        if not bench.empty:
            jobs = jobs.merge(bench.drop(columns=["rule", "target"]), on="key", how="left")
            jobs.loc[jobs["superseded"], [c for c in bench.columns
                                          if c not in ("rule", "target", "key")]] = None
        if not logs.empty:
            jobs = jobs.merge(logs.drop(columns=["rule", "target"]), on="key", how="left")
            jobs.loc[jobs["superseded"], [c for c in logs.columns
                                          if c not in ("rule", "target", "key")]] = None
        n_superseded = int(jobs["superseded"].sum())
        n_bench = int(jobs["s"].notna().sum()) if "s" in jobs else 0
        n_bench_expected = int(attributable["key"].isin(bench["key"] if not bench.empty else []).sum())
    else:
        n_superseded = n_bench = n_bench_expected = 0
    for c in ["s", "max_rss", "cpu_time", "mean_load", "io_in", "io_out",
              "warning_lines", "error_lines"]:
        jobs[c] = pd.to_numeric(jobs[c], errors="coerce") if c in jobs else float("nan")
    if "log_file" not in jobs:
        jobs["log_file"] = None

    # Per-rule rollup
    if not jobs.empty:
        nsum = lambda x: pd.to_numeric(x).sum(min_count=1)  # noqa: E731  (NaN, not 0, if no benchmark)
        rules = (jobs[jobs["rule"] != "all"].groupby("rule")
                 .agg(jobs=("jobid", "count"), total_s=("s", nsum), mean_s=("s", "mean"),
                      max_s=("s", "max"), wall_total_s=("wall_s", "sum"),
                      cpu_s=("cpu_time", nsum), max_rss_mb=("max_rss", "max"),
                      failed=("status", lambda x: int((x == "failed").sum())))
                 .reset_index())
        rules = rules.sort_values("total_s", ascending=False, na_position="last")
    else:
        rules = pd.DataFrame()

    # Run history (all runs, for index + figure)
    hist_rows = []
    for rid in ids:
        h = run_summary(rid, runs[rid], set()) if rid != run_id else S
        hist_rows.append({"run_id": rid, "status": h["status"], "wall_s": h["wall_s"],
                          "executed": h["executed"], "planned": h["meta"]["planned"],
                          "started": h["info"].get("started_utc") or h["info"].get("started", ""),
                          "git_commit": (h["info"].get("git_commit") or "")[:10],
                          "dirty": len(h["dirty"]), "host": h["info"].get("host", "")})
    history = pd.DataFrame(hist_rows)

    # ---------------- figures
    figs = {
        "timeline": fig_timeline(jobs, fig_dir / "timeline.png", run_id) if not jobs.empty else None,
        "runtime_by_rule": fig_runtime_by_rule(rules, fig_dir / "runtime_by_rule.png") if not rules.empty else None,
        "runtime_matrix": fig_runtime_matrix(jobs, fig_dir / "runtime_by_build.png") if not jobs.empty else None,
        "memory": fig_memory(jobs, fig_dir / "memory_by_rule.png") if not jobs.empty else None,
        "history": fig_history(history, fig_dir / "run_history.png"),
    }
    for stale in fig_dir.glob("*.png"):
        if stale not in [f for f in figs.values() if f]:
            stale.unlink()

    # ---------------- tables
    job_cols = ["jobid", "rule", "target", "subtype", "segment", "status", "start", "end",
                "wall_s", "s", "cpu_time", "max_rss", "mean_load", "io_in", "io_out",
                "warning_lines", "error_lines", "superseded", "log"]
    if not jobs.empty:
        jobs[[c for c in job_cols if c in jobs]].to_csv(tab_dir / "jobs.tsv", sep="\t", index=False)
        rules.to_csv(tab_dir / "rules.tsv", sep="\t", index=False)
    history.to_csv(tab_dir / "run_history.tsv", sep="\t", index=False)

    # ---------------- markdown
    rel = lambda p: os.path.relpath(p, out_dir)  # noqa: E731
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tz_note = (info.get("started", "").split() or [""])
    tz_note = tz_note[-2] if len(tz_note) >= 2 else "host"
    L = []
    L.append(f"# Run report · `{run_id}`\n")
    L.append(f"**Status: {S['status']}** · generated {now} by `scripts/run_report.py` "
             f"from `{run_dir}/`. Job times come from this run's Snakemake main log "
             f"(host clock, {tz_note}); runtime and memory come from per-job benchmarks.\n")

    L.append("## Provenance\n")
    started = info.get("started_utc") or (f"{meta['first_ts']:%Y-%m-%d %H:%M:%S} ({tz_note})"
                                          if meta["first_ts"] else info.get("started", "–"))
    finished = info.get("finished_utc") or (f"{meta['last_ts']:%Y-%m-%d %H:%M:%S} ({tz_note})"
                                            if meta["last_ts"] else "–")
    L.append(kv_table([
        ("Run ID", run_id),
        ("Status", S["status"]),
        ("Started", started),
        ("Finished", finished),
        ("Wall clock", fmt_dur(S["wall_s"])),
        ("Host", info.get("host", "–")),
        ("User", info.get("user") or info.get("whoami") or "–"),
        ("Working directory", f"`{info.get('workdir', '–')}`"),
        ("Git commit", f"`{info.get('git_commit', '–')}`"),
        ("Uncommitted changes", f"{len(S['dirty'])} file(s)" if S["dirty"] else "none (clean tree)"),
        ("Cores provided", meta["cores"] or "–"),
        ("Provenance file", f"`{rel(runs[run_id]['provenance'])}`" if runs[run_id].get("provenance") else "missing"),
        ("Main log", f"`{rel(runs[run_id]['main_log'])}`" if runs[run_id].get("main_log") else "missing"),
    ]))
    L.append("")
    if S["tools"]:
        L.append("**Tool versions**\n")
        L.append(kv_table(sorted(S["tools"].items())))
        L.append("")
    if S["dirty"]:
        L.append("<details><summary>Uncommitted changes at run start</summary>\n\n```\n"
                 + "\n".join(S["dirty"]) + "\n```\n</details>\n")

    L.append("## Summary\n")
    if meta["nothing_to_do"] or jobs.empty:
        L.append("Nothing was executed in this run (all outputs were up to date).\n")
    else:
        failed = jobs[jobs["status"] == "failed"]
        unfinished = jobs[jobs["status"] == "running"]
        tot_s = jobs["s"].sum(min_count=1)
        cpu_s = jobs["cpu_time"].sum(min_count=1)
        peak = jobs.loc[jobs["max_rss"].astype(float).idxmax()] if jobs["max_rss"].notna().any() else None
        busy = jobs["wall_s"].sum()
        eff = (busy / (S["wall_s"] * meta["cores"])) if S["wall_s"] and meta["cores"] else None
        L.append(kv_table([
            ("Jobs planned", meta["planned"] or "–"),
            ("Jobs executed", f"{len(jobs)} ({int((jobs['status'] == 'finished').sum())} finished, "
                              f"{len(failed)} failed, {len(unfinished)} unfinished)"),
            ("Summed job runtime", fmt_dur(tot_s)),
            ("Summed CPU time", fmt_dur(cpu_s)),
            ("Core utilisation", f"{eff:.0%} of {meta['cores']} cores over the wall clock" if eff else "–"),
            ("Slowest job", (lambda r: f"{r['rule']} / {r['target']} — {fmt_dur(r['s'])}")(
                jobs.loc[jobs['s'].astype(float).idxmax()]) if jobs["s"].notna().any() else "–"),
            ("Peak memory", f"{peak['max_rss']:.0f} MB — {peak['rule']} / {peak['target']}" if peak is not None else "–"),
            ("Benchmarks attributed", f"{n_bench} of {len(jobs) - n_superseded} jobs"),
        ]))
        L.append("")
        if n_superseded:
            L.append(f"> {n_superseded} job(s) from this run were re-executed by a later run, so "
                     f"their benchmark and log files now describe that later run and are left "
                     f"out of the runtime and memory figures here.\n")

        if figs["timeline"]:
            L.append("## Timeline\n")
            L.append(f"![Job timeline]({rel(figs['timeline'])})\n")
            L.append("Each bar is one job, coloured by subtype (grey = ingest/other); "
                     "red outline = failed. The top panel counts jobs running at once.\n")

        L.append("## Runtime\n")
        if figs["runtime_by_rule"]:
            L.append(f"![Runtime by rule]({rel(figs['runtime_by_rule'])})\n")
        if figs["runtime_matrix"]:
            L.append(f"![Runtime by build]({rel(figs['runtime_matrix'])})\n")
        if not rules.empty:
            L.append("Runtime, CPU and memory are from benchmarks; *wall (log)* is the summed "
                     "start-to-finish time from the main log (1 s resolution) and also covers "
                     "rules without a benchmark.\n")
            L.append(md_table(rules, ["rule", "jobs", "total_s", "mean_s", "max_s", "cpu_s", "max_rss_mb",
                                      "wall_total_s", "failed"],
                              ["rule", "jobs", "total", "mean", "max", "CPU", "peak MB", "wall (log)", "failed"],
                              {"total_s": fmt_dur, "wall_total_s": fmt_dur, "mean_s": fmt_dur, "max_s": fmt_dur, "cpu_s": fmt_dur,
                               "max_rss_mb": lambda v: "–" if pd.isna(v) else f"{v:.0f}"}))
            L.append("")
        if jobs["s"].notna().any():
            L.append("**Slowest 10 jobs**\n")
            top = jobs.dropna(subset=["s"]).sort_values("s", ascending=False).head(10)
            L.append(md_table(top, ["rule", "target", "s", "cpu_time", "max_rss", "start"],
                              ["rule", "target", "runtime", "CPU", "peak MB", "started"],
                              {"s": fmt_dur, "cpu_time": fmt_dur,
                               "max_rss": lambda v: "–" if pd.isna(v) else f"{v:.0f}",
                               "start": lambda v: "–" if pd.isna(v) else f"{v:%H:%M:%S}"}))
            L.append("")

        if figs["memory"]:
            L.append("## Memory\n")
            L.append(f"![Peak memory by rule]({rel(figs['memory'])})\n")

        L.append("## Failures and log checks\n")
        if failed.empty and unfinished.empty:
            L.append("No failed jobs.\n")
        for _, r in pd.concat([failed, unfinished]).iterrows():
            L.append(f"### ✗ {r['rule']} / {r['target']} ({r['status']})\n")
            lf = r.get("log_file") if isinstance(r.get("log_file"), str) else None
            if lf and Path(lf).exists():
                tail = Path(lf).read_text(errors="replace").splitlines()[-20:]
                L.append(f"Last lines of `{rel(lf)}`:\n\n```\n" + "\n".join(tail) + "\n```\n")
            else:
                L.append(f"Log: `{r['log'] or 'none'}`\n")
        flagged = jobs[(jobs["warning_lines"].fillna(0) > 0) | (jobs["error_lines"].fillna(0) > 0)]
        if not flagged.empty:
            flagged = flagged.sort_values(["error_lines", "warning_lines"], ascending=False).head(25)
            L.append("Job logs that mention warnings or errors (a mention is not necessarily a "
                     "problem — open the log to check):\n")
            L.append(md_table(flagged, ["rule", "target", "error_lines", "warning_lines", "log_file"],
                              ["rule", "target", "error lines", "warning lines", "log"],
                              {"error_lines": lambda v: int(v), "warning_lines": lambda v: int(v),
                               "log_file": lambda v: f"`{rel(v)}`" if isinstance(v, str) else "–"}))
            L.append("")

    L.append("## Run history\n")
    if figs["history"]:
        L.append(f"![Run history]({rel(figs['history'])})\n")
    L.append(md_table(history, ["run_id", "status", "started", "wall_s", "executed", "planned", "git_commit", "dirty"],
                      ["run", "status", "started", "wall clock", "jobs run", "jobs planned", "commit", "dirty files"],
                      {"wall_s": fmt_dur,
                       "run_id": lambda v: f"[{v}](../{v}/report.md)" if (run_dir / "reports" / v / "report.md").exists() or v == run_id else v,
                       "planned": lambda v: "–" if pd.isna(v) else int(v)}))
    L.append("")
    L.append("## Data files\n")
    L.append("- `tables/jobs.tsv` — one row per job: times from the main log joined to benchmark and log metrics\n"
             "- `tables/rules.tsv` — the per-rule rollup above\n"
             "- `tables/run_history.tsv` — every run found in `.run/run_logs/`\n"
             "- Benchmark columns follow Snakemake: `s` seconds, `max_rss` MB, `cpu_time` seconds, "
             "`io_in`/`io_out` MB, `mean_load` % CPU.\n")

    (out_dir / "report.md").write_text("\n".join(L))
    write_index(run_dir, history)
    if not quiet:
        print(f"run report: {out_dir / 'report.md'}")
    return out_dir


def write_index(run_dir, history):
    rep = run_dir / "reports"
    L = ["# Run reports\n",
         "One report per Snakemake run, built by `scripts/run_report.py` from `.run/`. "
         "Newest first.\n"]
    h = history.iloc[::-1]
    L.append(md_table(h, ["run_id", "status", "started", "wall_s", "executed", "git_commit", "dirty"],
                      ["run", "status", "started", "wall clock", "jobs run", "commit", "dirty files"],
                      {"wall_s": fmt_dur,
                       "run_id": lambda v: f"[{v}]({v}/report.md)" if (rep / v / "report.md").exists() else v}))
    (rep / "index.md").write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", default=".run", type=Path)
    ap.add_argument("--run-id", help="run to report on (default: the latest)")
    ap.add_argument("--all", action="store_true", help="rebuild the report for every run")
    a = ap.parse_args()

    runs = discover_runs(a.run_dir / "run_logs")
    if not runs:
        sys.exit(f"no runs found in {a.run_dir / 'run_logs'}")
    if a.all:
        targets = list(runs)
    elif a.run_id:
        if a.run_id not in runs:
            sys.exit(f"run {a.run_id} not found; known runs: {', '.join(runs)}")
        targets = [a.run_id]
    else:
        targets = [list(runs)[-1]]
    for rid in targets:
        build_report(rid, runs, a.run_dir)


if __name__ == "__main__":
    main()
