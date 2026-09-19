#!/usr/bin/env python3
"""Synchronize ROADMAP.md with GitHub issue states.

Queries the GitHub REST API for the three Kingdoms repositories, maps issue
states to roadmap statuses and rewrites ROADMAP.md in place: milestone table
rows, "Current Phase", "Out of Scope" and the change log.

Status mapping (docs/SKILLS/update-roadmap.md):
- closed as completed   -> done
- closed as not planned  -> dropped (row moved to "Out of Scope")
- open with a linked PR   -> in-review
- open, current status `in-progress` or `blocked` -> unchanged (manual judgment)
- open, otherwise        -> todo

The sibling repositories are public; when one is unreadable (rate limit,
missing token) the script warns and keeps its existing rows, like
scripts/validate_docs.py.

Exit codes: 0 success (or --check without drift), 1 drift detected in --check
mode, 2 fatal error.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://api.github.com"
OWNER = "merlin-pinpin"
REPOS = ("kingdoms", "kingdoms-services", "kingdoms-infra")
PER_PAGE = 100
MANUAL_STATUSES = ("in-progress", "blocked")
STATUSES = ("todo", "in-progress", "in-review", "done", "blocked", "dropped")

ROW_RE = re.compile(
    r"^\|\s*(?P<track>[^|]+?)\s*\|\s*(?P<repo>[\w.-]+)#(?P<num>\d+)\s*\|"
    r"\s*(?P<status>[a-z-]+)\s*\|$"
)
PHASE_HEADING_RE = re.compile(r"^### Phase (?P<num>\d+) —")
CURRENT_PHASE_RE = re.compile(r"^Phase (?P<num>\d+)\b")
CLOSING_REF_RE = re.compile(
    r"\b(?:close[ds]?|closing|fix(?:e[ds]?)?|fixing|resolv(?:e[ds]?)?|resolving)"
    r"[^#\n]*?(?:(?P<owner>[\w.-]+)/(?P<ref_repo>[\w.-]+))?"
    r"#(?P<num>\d+)",
    re.IGNORECASE,
)
BULLET_REF_RE = re.compile(r"\b(?P<repo>[\w.-]+)#(?P<num>\d+)\b")


@dataclass
class Issue:
    state: str
    state_reason: str | None
    title: str


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def api_get(path: str, token: str | None) -> list[dict]:
    """Return all pages of a GET request to the GitHub REST API.

    On an authentication failure (401/403) or a missing repo (404) the request
    is retried unauthenticated: all three Kingdoms repositories are public.
    Raises the last error when both attempts fail.
    """
    last_error: Exception | None = None
    for attempt_token in (token, None):
        items: list[dict] = []
        page = 1
        separator = "&" if "?" in path else "?"
        try:
            while True:
                url = f"{API_BASE}{path}{separator}per_page={PER_PAGE}&page={page}"
                request = urllib.request.Request(
                    url,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "kingdoms-roadmap-sync",
                    },
                )
                if attempt_token:
                    request.add_header("Authorization", f"Bearer {attempt_token}")
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = json.load(response)
                items.extend(data)
                if not isinstance(data, list) or len(data) < PER_PAGE:
                    return items
                page += 1
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in (401, 403, 404) or attempt_token is None:
                raise
        except urllib.error.URLError as error:
            last_error = error
            raise
    raise last_error if last_error else RuntimeError("unreachable")


def fetch_repo_state(
    repo: str, token: str | None
) -> tuple[dict[int, Issue], set[int]] | None:
    """Return ({number: Issue}, {numbers with an open linked PR}) or None."""
    try:
        raw_issues = api_get(f"/repos/{OWNER}/{repo}/issues?state=all", token)
    except (urllib.error.HTTPError, urllib.error.URLError) as error:
        warn(f"cannot read {OWNER}/{repo}: {error}; keeping its rows")
        return None

    issues = {
        item["number"]: Issue(
            state=item["state"],
            state_reason=item.get("state_reason"),
            title=item.get("title") or f"{repo}#{item['number']}",
        )
        for item in raw_issues
        if "pull_request" not in item
    }
    if not issues:
        warn(
            f"{OWNER}/{repo} returned no issues; the GitHub API may have "
            f"rejected the token silently (check the issues:read permission)"
        )

    linked: set[int] = set()
    try:
        pulls = api_get(f"/repos/{OWNER}/{repo}/pulls?state=open", token)
    except (urllib.error.HTTPError, urllib.error.URLError) as error:
        warn(f"cannot list open PRs of {OWNER}/{repo}: {error}; no PR detection")
        pulls = []
    for pull in pulls:
        for match in CLOSING_REF_RE.finditer(pull.get("body") or ""):
            ref_repo = match["ref_repo"]
            if ref_repo and ref_repo != repo:
                continue
            linked.add(int(match["num"]))
    return issues, linked


def compute_status(
    issue: Issue, has_pr: bool, current: str
) -> str:
    if issue.state == "closed":
        return "dropped" if issue.state_reason == "not_planned" else "done"
    if has_pr:
        return "in-review"
    if current in MANUAL_STATUSES:
        return current
    return "todo"


def sync_roadmap(
    text: str,
    states: dict[str, tuple[dict[int, Issue], set[int]]],
    today: str,
) -> tuple[str, list[str], list[str]]:
    """Return (new text, change summaries, warnings)."""
    lines = text.splitlines()
    warnings: list[str] = []
    changes: list[str] = []
    dropped: list[tuple[str, int, str]] = []
    phase_status: dict[int, list[str]] = defaultdict(list)
    referenced: dict[str, set[int]] = defaultdict(set)
    row_status: dict[int, str] = {}

    section: int | str | None = None
    for index, line in enumerate(lines):
        phase_match = PHASE_HEADING_RE.match(line)
        if phase_match:
            section = int(phase_match["num"])
            continue
        if line.startswith("### Sub-tasks"):
            section = "subtasks"
            continue
        if line.startswith("## "):
            section = None
            continue
        if section is None:
            continue
        row = ROW_RE.match(line)
        if not row:
            continue
        repo = row["repo"]
        num = int(row["num"])
        current = row["status"]
        if repo not in REPOS:
            warnings.append(f"unknown repository reference '{repo}#{num}'")
            continue
        state = states.get(repo)
        if state is None:
            continue
        issues, linked = state
        issue = issues.get(num)
        if issue is None:
            warnings.append(f"issue {repo}#{num} not found on GitHub; keeping its row")
            continue
        status = compute_status(issue, num in linked, current)
        row_status[index] = status
        if status == "dropped":
            dropped.append((repo, num, issue.title))
            if current != "dropped":
                changes.append(f"{repo}#{num} {current}->dropped (moved to Out of Scope)")
        elif status != current:
            changes.append(f"{repo}#{num} {current}->{status}")
        if isinstance(section, int):
            phase_status[section].append(status)
        referenced[repo].add(num)

    for repo, state in states.items():
        issues, _linked = state
        for num, issue in issues.items():
            if issue.state == "open" and num not in referenced[repo]:
                warnings.append(
                    f"open issue {repo}#{num} ({issue.title}) is not listed in "
                    f"ROADMAP.md; add it to the matching phase or Sub-tasks table"
                )

    if not changes:
        return text, changes, warnings

    out: list[str] = []
    in_out_of_scope = False
    out_of_scope_buffer: list[str] = []
    current_phase: int | None = None
    for phase, statuses in sorted(phase_status.items()):
        if any(status != "done" for status in statuses):
            current_phase = phase
            break
    replace_next_phase_line = current_phase is not None or any(row_status.values())

    for index, line in enumerate(lines):
        if line.startswith("## Out of Scope"):
            in_out_of_scope = True
            out.append(line)
            continue
        if in_out_of_scope:
            if line.startswith("## "):
                while out_of_scope_buffer and out_of_scope_buffer[-1] == "":
                    out_of_scope_buffer.pop()
                for repo, num, title in dropped:
                    out_of_scope_buffer.append(
                        f"- {title} — dropped, see {repo}#{num} (closed as not planned)"
                    )
                out.extend(out_of_scope_buffer)
                out.append("")
                out_of_scope_buffer = []
                in_out_of_scope = False
                out.append(line)
                continue
            out_of_scope_buffer.append(line)
            ref = BULLET_REF_RE.search(line)
            if ref and ref["repo"] in states:
                issue = states[ref["repo"]][0].get(int(ref["num"]))
                if issue is not None and issue.state == "open":
                    warnings.append(
                        f"{ref['repo']}#{ref['num']} is listed in Out of Scope "
                        f"but is open again; move it back manually"
                    )
            continue
        if index in row_status:
            status = row_status[index]
            if status == "dropped":
                continue
            row = ROW_RE.match(line)
            if row["status"] != status:
                line = ROW_RE.sub(
                    lambda m: f"| {m['track']} | {m['repo']}#{m['num']} | {status} |",
                    line,
                )
        if replace_next_phase_line and CURRENT_PHASE_RE.match(line):
            if current_phase is None:
                out.append("All phases complete")
                changes.append("current phase -> all phases complete")
            else:
                old = int(CURRENT_PHASE_RE.match(line)["num"])
                if old != current_phase:
                    changes.append(f"current phase {old}->{current_phase}")
                out.append(
                    CURRENT_PHASE_RE.sub(f"Phase {current_phase}", line, count=1)
                )
            replace_next_phase_line = False
            continue
        out.append(line)

    if in_out_of_scope and dropped:
        while out_of_scope_buffer and out_of_scope_buffer[-1] == "":
            out_of_scope_buffer.pop()
        for repo, num, title in dropped:
            out_of_scope_buffer.append(
                f"- {title} — dropped, see {repo}#{num} (closed as not planned)"
            )
        out.extend(out_of_scope_buffer)
        out.append("")

    summary = "; ".join(changes[:5])
    if len(changes) > 5:
        summary += f"; (+{len(changes) - 5} more)"
    change_row = f"| {today} | auto-sync: {summary} |"
    if change_row not in out:
        while out and out[-1] == "":
            out.pop()
        out.append(change_row)
    return "\n".join(out) + "\n", changes, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing; exit 1 when the roadmap would change",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub API token (default: the GITHUB_TOKEN environment variable)",
    )
    parser.add_argument(
        "--roadmap",
        type=Path,
        default=repo_root() / "ROADMAP.md",
        help="path to ROADMAP.md (default: the repository root)",
    )
    args = parser.parse_args()

    text = args.roadmap.read_text(encoding="utf-8")
    states: dict[str, tuple[dict[int, Issue], set[int]] | None] = {}
    for repo in REPOS:
        states[repo] = fetch_repo_state(repo, args.token)
    known = {repo: state for repo, state in states.items() if state is not None}
    if not known:
        warn("no repository could be read; aborting")
        return 2

    today = datetime.now(timezone.utc).date().isoformat()
    new_text, changes, warnings = sync_roadmap(
        text, known, today  # type: ignore[arg-type]
    )
    for warning in warnings:
        warn(warning)

    if new_text == text:
        print("ROADMAP.md is up to date")
        return 0

    if args.check:
        diff = difflib.unified_diff(
            text.splitlines(), new_text.splitlines(),
            fromfile=str(args.roadmap), tofile=str(args.roadmap), lineterm="",
        )
        for line in diff:
            print(line)
        print(f"ROADMAP.md is out of date ({len(changes)} changes needed)")
        return 1

    args.roadmap.write_text(new_text, encoding="utf-8")
    for change in changes:
        print(change)
    print(f"ROADMAP.md updated ({len(changes)} changes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
