# Business Requirements — 如鸢 (Ru Yuan) 突发情况 Team Optimizer

> Status: **v1 built and in use.** Core scoring rules, data pipeline, and UI are implemented and
> verified end-to-end.

This document has been split into focused files under [docs/](docs/), organized by concern so an
editor only needs to load what's relevant to the file being changed. **Start at
[CLAUDE.md](CLAUDE.md)** for the full index of which file covers what:

- [docs/product-overview.md](docs/product-overview.md) — background, problem, goals/non-goals, users, success criteria, glossary
- [docs/data-model.md](docs/data-model.md) — wiki data sources, scrapers, data schemas, persistence
- [docs/business-rules.md](docs/business-rules.md) — squad scoring, recommendation modes
- [docs/ui-flows.md](docs/ui-flows.md) — user flow, page layout, inputs/outputs
- [docs/decisions-log.md](docs/decisions-log.md) — constraints, resolved/open decisions

Update the relevant doc whenever scope, data shape, or rules change — code should follow these
docs, not the other way around.
