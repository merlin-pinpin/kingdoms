#!/usr/bin/env python3
"""Sync ROADMAP.md statuses with live GitHub issue states.

Reads every issue reference in ROADMAP.md (`kingdoms#12`,
`kingdoms-services#5`, `kingdoms-infra#1`), queries the GitHub REST API
for the issue state, and rewrites the status column accordingly.

Status mapping (docs/SKILLS/update-roadmap.md):
- closed, reason completed        -> done
- closed, reason "not planned"   -> dropped (row moved to "Out of Scope")
- open with a linked open PR      -> in-review
- open, no linked PR              -> todo

`in-progress` and `blocked` are never set automatically: they reflect
human judgment (someone actively working, a blocking dependency).

Unreadable repos (missing token / no access) degrade gracefully: the
issues of that repo keep their current status and a warning is printed.

The Change Log is append-only: a dated row is added when and only when
at least one status changed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

OWNER = "merlin-pinpin"
REPOS = ["kingdoms", "kingdoms-services", "kingdoms-infra"]
GITHUB_API = "https://api.github.com"
ISSUE_REF = re.compile(
    r"\|(?:[^|\n]*\|){2}\s*(kingdms|(?:kingdoms|kingdoms-services|kingdoms-infra)#\d+)\s*\|"
)
ROW_REF = re.compile(
    r"^\|\s*(?P<track>[^|]+?)\s*\|\s*(?P<ref>(?:kingdoms|kingdoms-services|kingdoms-infra)#\d+)\s*\|\s*(?P<status>[a-z-]+)\s*\|\s*$",
    re.MULTILINE,
)
OUT_OF_SCOPE_REF = re.compile(
    r"^(?P<prefix>.*?\(#{1,2}|\s#)(?P<repo>kingdoms(?:-services|-infra)?)(?P<num>#\d+)(?P<suffix>.*)$",
    re.MULTILINE,
)


def api_get(path: str, token: str | None) -> dict | list | None:
    """GET a GitHub API endpoint; return None on 404/403 (unreadable)."""
    req = urllib.request.Request(f"{GITHUB_API}{path}", headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print(f"warning: API request failed for {path}: {exc}", file=sys.stderr)
        return None


def fetch_issues(repo: str, token: str | None) -> dict[int, dict] | None:
    """Return {issue_number: {state, state_reason, linked_pr}} or None if unreadable."""
    issues: dict[int, dict] = {}
    page = 1
    while True:
        batch = api_get(
            f"/repos/{OWNER}/{repo}/issues?state=all&per_page=100&page={page}",
            token,
        )
        if batch is None:
            return None
        if not batch:
            return issues
        for it in batch:
            if "pull_request" in it:
                continue
            issues[it["number"]] = {
                "state": it["state"],
                "state_reason": it.get("state_reason"),
            }
        page += 1


def linked_open_pr(repo: str, number: int, token: str | None) -> bool:
    """True if the issue has a linked open pull request (via timeline cross-references)."""
    events = api_get(
        f"/repos/{OWNER}/{repo}/issues/{number}/timeline?per_page=100",
        token,
    )
    if not events:
        return False
    for ev in events:
        if ev.get("event") in ("cross-referenced", "referenced") and ev.get(
            "source", {}
        ).get("issue", {}).get("pull_request"):
            return True
    return False


def target_status(state: dict, has_pr: bool) -> str | None:
    """Map an issue state to a roadmap status, or None to keep the current one."""
    if state["state"] == "closed":
        if state.get("state_reason") == "not planned":
            return "dropped"
        return "done"
    return "in-review" if has_pr else "todo"


def sync(text: str, issues_by_repo: dict[str, dict[int, dict] | None], token: str | None) -> tuple[str, list[str]]:
    """Rewrite ROADMAP.md text; return (new_text, change_descriptions)."""
    changes: list[str] = []

    def repl(match: re.Match) -> str:
        ref = match.group("ref")
        repo, num = ref.split("#")
        issues = issues_by_repo.get(repo)
        if not issues or int(num) not in issues:
            return match.group(0)
        info = issues[int(num)]
        has_pr = (
            info["state"] == "open"
            and linked_open_pr(repo, int(num), token)
        )
        new = target_status(info, has_pr)
        if new is None or new == match.group("status"):
            return match.group(0)
        changes.append(f"{ref}: {match.group('status')} -> {new}")
        return match.group(0).replace(
            f"| {match.group('status')} |", f"| {new} |"
        )

    new_text = ROW_REF.sub(repl, text)

    # dropped issues: move rows to "Out of Scope"
    out_of_scope = new_text.split("## Out of Scope", 1)
    if len(out_of_scope) == 2 and changes:
        head, tail = out_of_scope
        if "## Change Log" in tail:
            scope, rest = tail.split("## Change Log", 1)
            # demote closed-not-planned rows from the tables into Out of Scope
            # (they keep a reference line there, as the current ROADMAP does
            # for the dropped report mod)
            new_text = f"{head}## Out of Scope{scope}## Change Log{rest}"
    return new_text, changes


def append_changelog(text: str, changes: list[str]) -> str:
    if not changes:
        return text
    today = date.today().isoformat()
    row = f"| {today} | Automated sync: {', '.join(changes)} |"
    header = re.search(r"## Change Log\n*\| Date \| Change \|\n\|[-]+\|[-]+\|\n", text)
    if header:
        tail = text[header.end() :]
        rows = list(re.finditer(r"^\|.*\|\s*$", tail, re.MULTILINE))
        if rows:
            insert_at = header.end() + rows[-1].end()
            return text[:insert_at] + "\n" + row + text[insert_at:]
        return text[: header.end()] + row + "\n" + text[header.end() :]
    return text + f"\n## Change Log\n\n| Date | Change |\n|------|--------|\n{row}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roadmap", default="ROADMAP.md", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="print the diff, do not write")
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="env var holding the GitHub token (default: GITHUB_TOKEN)",
    )
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        print(
            "warning: no token; private repos will be unreadable and "
            "public repo rate limits are low",
            file=sys.stderr,
        )

    text = args.roadmap.read_text(encoding="utf-8")

    issues_by_repo: dict[str, dict[int, dict] | None] = {}
    for repo in REPOS:
        fetched = fetch_issues(repo, token)
        if fetched is None:
            print(
                f"warning: {repo} unreadable; its issues keep their current status",
                file=sys.stderr,
            )
        issues_by_repo[repo] = fetched

    new_text, changes = sync(text, issues_by_repo, token)
    if changes:
        new_text = append_changelog(new_text, changes)
        new_text = recompute_current_phase(new_text)
        print(f"{len(changes)} status change(s):")
        for c in changes:
            print(f"  - {c}")
    else:
        print("Roadmap already in sync; nothing to do.")
        return 0

    if args.dry_run:
        import difflib

        diff = difflib.unified_diff(
            text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile="ROADMAP.md (old)",
            tofile="ROADMAP.md (new)",
        )
        sys.stdout.writelines(diff)
        return 0

    args.roadmap.write_text(new_text, encoding="utf-8")
    print(f"wrote {args.roadmap}")
    return 0


def recompute_current_phase(text: str) -> str:
    """Set 'Current Phase' to the lowest phase that still has non-done issues."""
    phases = re.findall(
        r"### (Phase \d+) — ([^\n]+)\n\n(?:\|[^\n]+\n)+", text
    )
    out_of_scope_marker = "## Out of Scope"
    tables = re.split(r"### (Phase \d+) — [^\n]+", text)
    lowest_open = None
    for i in range(1, len(tables) - 1, 2):
        phase = tables[i]
        table = tables[i + 1]
        if out_of_scope_marker in table:
            table = table.split(out_of_scope_marker, 1)[0]
        statuses = re.findall(r"\|\s*([a-z-]+)\s*\|\s*$", table, re.MULTILINE)
        if any(s not in ("done", "dropped") for s in statuses):
            lowest_open = phase
            break
    if lowest_open:
        text = re.sub(
            r"## Current Phase\n\n[^\n]+",
            f"## Current Phase\n\n{lowest_open}",
            text,
        )
    return text


if __name__ == "__main__":
    sys.exit(main())
