# Kingdoms Roadmap

> Single source of truth for project progress. Updated via the
> [Update roadmap](docs/SKILLS/update-roadmap.md) skill.

Status values: `todo` / `in-progress` / `in-review` / `done` / `blocked` / `dropped`.

## Current Phase
Phase 1 — Foundations (repos structure, architecture docs)

## Milestones

### Phase 1 — Foundations
| Track | Issue | Status |
|-------|-------|--------|
| kingdoms: repo structure | kingdoms#1 | done |
| kingdoms: architecture docs | kingdoms#2 | done |
| kingdoms: docs CI | kingdoms#3 | done |
| kingdoms: WORKFLOWS.md | kingdoms#4 | done |
| kingdoms: MODS docs | kingdoms#5 | done |
| kingdoms: ADRs | kingdoms#6 | done |
| kingdoms: governance (LICENSE, CLA) | kingdoms#11 | done |
| kingdoms: ROADMAP + skill | kingdoms#9 | done |
| kingdoms: vibe-coding workflow doc | kingdoms#10 | done |
| services: repo structure | kingdoms-services#1 | todo |
| services: MockDiscord | kingdoms-services#2 | todo |
| infra: repo structure | kingdoms-infra#1 | todo |

### Phase 2 — Core
| Track | Issue | Status |
|-------|-------|--------|
| services: IPlatform | kingdoms-services#3 | todo |
| services: DB models | kingdoms-services#4 | todo |
| services: ChannelService | kingdoms-services#5 | todo |
| services: WorkflowEngine | kingdoms-services#6 | todo |
| services: enums | kingdoms-services#7 | todo |
| services: adapters | kingdoms-services#8 | todo |
| services: StateService | kingdoms-services#9 | todo |
| services: exceptions | kingdoms-services#10 | todo |
| services: config system | kingdoms-services#16 | todo |
| services: i18n | kingdoms-services#17 | todo |
| infra: CI/CD | kingdoms-infra#2 | todo |
| infra: infra docs | kingdoms-infra#3 | todo |
| infra: deployment scripts | kingdoms-infra#4 | todo |
| infra: monitoring | kingdoms-infra#5 | todo |

### Phase 3 — Mods & Discord
| Track | Issue | Status |
|-------|-------|--------|
| services: DiscordPlatform | kingdoms-services#11 | todo |
| services: Bot structure | kingdoms-services#12 | todo |
| services: UI components | kingdoms-services#13 | todo |
| services: registration mod | kingdoms-services#14 | todo |
| services: ladder mod | kingdoms-services#15 | todo |
| services: clans mod | kingdoms-services#19 | todo |
| services: admin mod | kingdoms-services#21 | todo |
| services: deployment scripts | kingdoms-services#20 | todo |
| services: semantic release | kingdoms-services#28 | todo |

### Sub-tasks
| Sub-task | Parent | Status |
|----------|--------|--------|
| Unit tests core | kingdoms-services#22 | todo |
| Mongo+Redis caching | kingdoms-services#23 | todo |
| MockDiscord framework | kingdoms-services#24 | todo |
| Registration DM flow | kingdoms-services#25 | todo |
| Channel/role mgmt | kingdoms-services#26 | todo |
| AoE2 game service | kingdoms-services#27 | todo |
| Docs architecture | kingdoms#7 | done |
| discord.py guide | kingdoms#8 | done |

## Out of Scope
- Report mod (`/report` command) — dropped, see kingdoms-services#18
  (closed as not planned)
- Twitch/Telegram platforms — architecture-ready (`IPlatform`), not implemented

## Change Log
| Date | Change |
|------|--------|
| 2026-09-18 | Initial roadmap (kingdoms#9), synced with GitHub issue states |
| 2026-09-18 | kingdoms#3 in-review (PR #21); session PRs #12-#21 opened for kingdoms#1-#6, #8-#11 |
| 2026-09-18 | kingdoms#1-#6, #9-#11 done (PRs #12-#21 merged); kingdoms#7 remaining: Key Principles + architecture sub-pages |
| 2026-09-18 | kingdoms#7 done: Key Principles in README, architecture/{core,mods,testing}.md deep-dives, cross-references |
