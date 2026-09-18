# Skill: Update roadmap

Keep `ROADMAP.md` (repo root) in sync with the actual GitHub issue states
across the three Kingdoms repos.

**This skill is automated.** The `sync-roadmap.yml` workflow runs
`scripts/sync_roadmap.py` on every issue/PR state change (plus a weekly
schedule) and opens or updates a single rolling PR
(`docs(roadmap): sync with GitHub issues`, branch `automation/roadmap-sync`).
See kingdoms#27.

Use this skill only to **verify** the automation (or to fix it when it is
broken), and to handle what the automation deliberately does not do.

## What the automation handles

| GitHub state | Roadmap status |
| ------------ | --------------- |
| closed as completed | `done` |
| closed as not planned | `dropped` |
| open + linked PR | `in-review` |
| open, no PR | `todo` |

Unreadable sibling repos (missing `ROADMAP_SYNC_TOKEN`): issues keep their
current status, warning printed, exit 0.

The automation also appends the Change Log row and recomputes the Current
Phase (lowest phase with a non-`done`/`dropped` issue).

## What stays manual

- `in-progress` and `blocked`: they reflect human judgment (someone
  actively working, a blocking dependency). The automation never sets
  them; if it sees them, it leaves them alone only if the issue is open.
  **Check these two values yourself** — the automation may overwrite
  `in-progress` with `in-review`/`todo` if a PR state changed.
- Moving rows to "Out of Scope": `dropped` is set in the status column;
  the manual part is writing the prose line in the Out of Scope section.
- Adding rows for newly created issues (the automation only updates
  statuses of referenced issues, it does not discover new ones).

## Procedure (verification / manual fallback)

1. Check the rolling PR: is there an open
   `docs(roadmap): sync with GitHub issues` PR? If yes, review and merge
   it — done.
2. If the workflow failed or the roadmap looks stale, run locally:
   ```bash
   gh workflow run sync-roadmap.yml --repo merlin-pinpin/kingdoms
   ```
   or, as a manual fallback:
   ```bash
   GITHUB_TOKEN=$(gh auth token) python3 scripts/sync_roadmap.py --dry-run
   ```
3. For the manual parts above, edit `ROADMAP.md` and open a PR titled
   `docs(roadmap): sync with GitHub issues` (any branch; do not stack on
   the automation branch).

## Rules

- Never invent statuses: every automated row must reflect an actual
  GitHub issue state.
- The Change Log is append-only.
- A manual sync PR must only touch `ROADMAP.md` (+ prose in Out of
  Scope).
- Do not reorder tables; keep tracks grouped by repo.

## Status values

`todo` / `in-progress` / `in-review` / `done` / `blocked` / `dropped`

## See also

- [../../ROADMAP.md](../../ROADMAP.md) — the roadmap this skill maintains
- [../../scripts/sync_roadmap.py](../../scripts/sync_roadmap.py) — the sync script
- [../../AGENTS.md](../../AGENTS.md) — the session-end rule that references this skill
- kingdoms#27 — automation tracking issue
