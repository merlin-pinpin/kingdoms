[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

# Kingdoms

Kingdoms is a modular Discord bot platform, built and maintained through a
vibe-coding workflow. It is the successor of JeanJack.

This repository is the **source of truth** for the project: it hosts all
architecture documentation, game workflows, mods documentation (rules and
environment), Architecture Decision Records (ADRs), and auto-generated
development docs. No application code lives here.

## Repositories

| Repository | Purpose |
| ---------- | ------- |
| [kingdoms](https://github.com/merlin-pinpin/kingdoms) (this repo) | Documentation: architecture, workflows, ADRs, mods docs, generated dev docs |
| [kingdoms-services](https://github.com/merlin-pinpin/kingdoms-services) | All Python code: generic core, Discord platform, mods, YAML configs |
| [kingdoms-infra](https://github.com/merlin-pinpin/kingdoms-infra) | Docker, CI/CD, GitOps manifests, deployment scripts |

## Key Principles

1. **Platform-agnostic core**: all game logic lives in `kingdoms-services/src/kingdoms/core/`, behind the `IPlatform` interface. Discord is one implementation; Twitch/Telegram can be added later without touching game logic.
2. **Modular mods**: each game feature (register, ladder, clans, ...) is a self-contained mod that declares its channels and roles via its YAML config (`kingdoms-services/config/mods/<mod>.yaml`) and documents its rules in `docs/MODS/<mod-name>/`.
3. **MongoDB only** (no relational DB) for durable state, with **Redis** for cache and distributed locks.
4. **Full-stack testing**: `MockDiscord` provides an in-memory `IPlatform` simulation; no test touches the real Discord API.
5. **i18n by default**: English is the default, French is available; all user-facing strings come from YAML locale files.

## Documentation structure

```
kingdoms/
├── README.md                      # This overview
├── AGENTS.md                      # Rules for AI coding agents
├── docs/
│   ├── ARCHITECTURE.md            # Technical architecture (Mermaid diagrams)
│   ├── WORKFLOWS.md               # Game workflows (registration, ladder, ...)
│   ├── MODS/                      # Mods documentation
│   │   ├── register/              # Registration mod (rules, environment)
│   │   ├── ladder/                # Ladder mod (rules, environment)
│   │   └── TEMPLATE/              # Template referenced by new mod docs
│   ├── DEVELOPMENT/               # Auto-generated technical docs
│   │   ├── api/                   # Generated API docs
│   │   └── pydoc/                 # Generated pydoc HTML
│   └── DECISIONS/                 # Architecture Decision Records (ADR)
├── .github/workflows/             # Docs generation and validation workflows
├── scripts/                       # Doc generation and validation scripts
└── templates/                     # Reusable templates (mods, ADRs)
```

## Key documents

- [AGENTS.md](AGENTS.md) — rules every AI coding agent must follow in this repo
- [ROADMAP.md](ROADMAP.md) — project phases and issue status (updated via the "Update roadmap" skill)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — technical architecture
- [docs/architecture/](docs/architecture/) — deep-dives: core design, mod system, discord.py components, testing
- [docs/WORKFLOWS.md](docs/WORKFLOWS.md) — game workflows
- [docs/DECISIONS/](docs/DECISIONS/) — architecture decision records
- [docs/MODS/](docs/MODS/) — mods documentation

## Contributing

Contributions are made through the vibe-coding workflow:

1. Work is tracked in [GitHub issues](https://github.com/merlin-pinpin/kingdoms/issues).
2. Each issue is developed on a dedicated `vibe/<short-slug>` branch.
3. A draft pull request is opened for every issue and reviewed before merge.
4. Documentation must be in **English**; game-related examples may be in French
   for i18n purposes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide and
the CLA process.

## License

Kingdoms is licensed under the [GNU Affero General Public License v3.0](LICENSE).
AGPL-3.0 was chosen so that any fork operated as a service must publish its
modified source to its users (§13) — a direct deterrent for competitive
privatization, since a bot is inherently a network service. External
contributors sign the [CLA](CLA.md), which preserves a relicensing option for
the project owner.
