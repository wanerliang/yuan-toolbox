# Business Requirements — Product Overview

*(Part of the split business-requirements doc — see [CLAUDE.md](../CLAUDE.md) for the full
section index and which file covers what.)*

> Status: **v1 built and in use.** Core scoring rules, data pipeline, and UI are implemented and
> verified end-to-end; remaining items in [decisions-log.md](decisions-log.md#13-open-questions)
> are refinements, not blockers. This document set is the source of truth for *why* the app exists
> and *what* it must do. Update it whenever scope, data shape, or rules change — code should
> follow this doc, not the other way around.

## 1. Background

**如鸢 (Ru Yuan)** is a mobile game. Certain side tasks **鸢报-突发情况 (sudden request)** require the player to select
a squad of **3–5 characters** from the roster they've obtained to complete the task.

Character choice matters beyond raw stats: many characters belong to a **羁绊 (buff connection)**
— a named combination of **2 or 3 specific characters** (not always just a pair) that grants a
synergy bonus, or occasionally a penalty, when *all* members of that combination are in the same
squad. Manually cross-referencing which combinations are covered, while also satisfying whatever
the quest itself demands, is tedious and error-prone to do by hand — especially as the roster grows.

## 2. Problem Statement

Given:
- a **quest scenario** (what the task requires), and
- the player's **owned characters** and their **buff-connection data**,

manually finding the best 3–5 character squad requires checking every relevant pairing by hand.
This tool automates that search and returns the most suitable squad(s).

## 3. Goals

- Given a selected quest scenario, recommend the best 3–5 character squad(s) from the
  player's available roster.
- Correctly account for 羁绊 (character combinations) when scoring a candidate squad — a squad
  that fully contains a positive-value 羁绊 should generally outscore one that doesn't, and a
  squad that fully contains a negative-value (debuff) 羁绊 should generally be penalized.
- Let the player re-run recommendations quickly as their roster or the quest changes (this is a
  personal planning tool used repeatedly, not a one-off report).
- Track which 羁绊 the player has already triggered, so they can systematically work through
  every possible combination (e.g. for an in-game achievement) without losing track of what's left.
- Support two recommendation-list scoring modes (highest score, unmarked-first for achievement
  progress) for the same (目标, 天气) instance, each reversible (enabling deliberate
  underperformance via reversed highest-score) — not just a single "best squad" view. See
  [business-rules.md §8.1](business-rules.md#81-recommendation-list-modes).

## 4. Non-Goals

- Not a general-purpose game database/wiki — only stores what's needed to compute recommendations.
- No cloud hosting / external database — runs via `streamlit run app.py`, with local
  username/password accounts (see [data-model.md §6.5](data-model.md#65-authentication--multi-user-accounts))
  rather than a third-party identity provider or hosted user directory. **Revised**: multi-user
  support (multiple independent accounts against one deployed instance) is now in scope — this
  was originally a Non-Goal ("single player... no user accounts, multi-user support") when the
  app was a purely local single-player tool; see [§5](#5-users) and
  [decisions-log.md §11](decisions-log.md#11-constraints).
- Not live-scraping the wiki at runtime or auto-syncing on a schedule — import is a manual,
  occasional step the user triggers when the game updates (see
  [data-model.md §6.1](data-model.md#61-character-buff-connection-羁绊-data)).
- Not modeling full battle simulation (turn order, damage rolls, RNG) unless a future rule
  requires it — start with a scoring/filtering model, not a simulator.
- **Sudden Request (鸢报-突发情况) is the only quest scenario type in scope.** No other quest
  types will be supported by this project.

## 5. Users

- Multiple independent users (e.g. the app owner plus friends/family they invite), each with
  their own owned-character selection and 羁绊 collection progress, all playing 如鸢 and planning
  squad choices for side quests against a single deployed instance. **Revised** from an earlier
  single-user-only design — see [data-model.md §6.5](data-model.md#65-authentication--multi-user-accounts)
  for how per-user accounts and data isolation work.

## 12. Success Criteria

- For a given quest scenario and roster, the app returns a squad recommendation faster and more
  reliably than manually cross-referencing the wiki by hand.
- Recommendations visibly reflect active 羁绊 (the user can trust *why* a squad was picked, not
  just trust the ranking blindly), including warning when a squad would trigger a debuff.

## 14. Glossary

| Term (EN) | Term (中文) | Notes |
|---|---|---|
| Character | 角色 | Unit the player has obtained |
| Secret Agent (category) | 密探 | The wiki's category name for all playable characters — source of the full 119-character roster ([data-model.md §6.2](data-model.md#62-players-owned-characters)), distinct from 密探羁绊 (the 羁绊 data page, [data-model.md §6.1](data-model.md#61-character-buff-connection-羁绊-data)) |
| Avatar | 头像 | Small square character portrait image, scraped alongside the roster ([data-model.md §6.2](data-model.md#62-players-owned-characters)) |
| Buff connection / combination | 羁绊 / 组合 | Named set of 2-3 specific characters granting a bonus (or penalty) when all are in the squad |
| Quest / side task | 任务 | The scenario being optimized for |
| Squad | 队伍 | The 3–5 selected characters |
| Sudden Request | 鸢报-突发情况 | A quest scenario defined by one 目标 + one 天气 combination |
| Target | 目标 | 8 values: 纵火, 传谣, 下毒, 卧底, 搜集, 灭火, 净水, 营救 |
| Weather | 天气 | 8 values: 晴天, 雨天, 大雾, 狂风, 小雪, 大雪, 飓风, 雷鸣 |
