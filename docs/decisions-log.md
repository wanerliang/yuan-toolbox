# Business Requirements — Constraints & Decisions Log

*(Part of the split business-requirements doc — see [CLAUDE.md](../CLAUDE.md) for the full
section index and which file covers what.)*

## 11. Constraints

- Python + Streamlit, runs locally or on a simple deployment target — no external cloud database
  or third-party identity provider required, even with multi-user accounts (see
  [data-model.md §6.5](data-model.md#65-authentication--multi-user-accounts)).
- Buff-connection data ([data-model.md §6.1](data-model.md#61-character-buff-connection-羁绊-data))
  and the full character roster + avatars
  ([data-model.md §6.2](data-model.md#62-players-owned-characters)) remain **local files bundled
  with/beside the app** (`data/buff_connections.csv`, `data/characters.csv`,
  `assets/characters/*.png`, `assets/weather/*.png`) — shared read-only reference data, the same
  for every user. The scraped data changes only on game updates (manual re-import).
- Owned-character flags (§6.2) and used-pair flags
  ([data-model.md §6.4](data-model.md#64-used-pair-tracking-achievement-progress)) are per-user
  and live in a local **SQLite** database (`data/app.db`), not a hosted/cloud database — read and
  rewritten by the app itself as each logged-in user interacts with it, partitioned by `user_id`.
  **Revised** from the original design's single shared JSON files
  (`data/owned_characters.json`/`data/used_pairs.json`), which couldn't distinguish one user's
  data from another's. SQLite was chosen over one-JSON-file-per-user specifically because it
  handles concurrent writes from multiple simultaneous sessions correctly.
- Login accounts are local username/password entries in `.streamlit/auth_config.yaml`
  (gitignored — bcrypt hashes + a cookie secret), managed via `scripts/manage_users.py`, not a
  hosted user directory or OAuth app — kept consistent with the "no cloud infra" constraint above.
- **Free-host redeploys reset local disk**: most free hosting (Streamlit Community Cloud
  included) resets the app's filesystem to match the GitHub repo on every redeploy — survives
  sleep/wake in between, not a rebuild. Accepted as-is for `data/app.db` (a redeploy loses
  everyone's saved characters/progress — judged acceptable for a small free personal deployment,
  not worth the added complexity to fix right now). Mitigated for the other two pieces of
  local-only state via `utils/bootstrap.py` — see
  [data-model.md §6.5](data-model.md#65-authentication--multi-user-accounts) — which re-fetches
  gitignored image assets and restores `.streamlit/auth_config.yaml` from a Streamlit secret on a
  fresh deploy.

## 13. Open Questions

- [x] ~~Write and run the scraper against `wiki.biligame.com/yuan/密探羁绊`~~ — done,
      `scripts/scrape_buff_connections.py` + `data/buff_connections.csv` (1207 rows), with a
      `data/buff_connections_overrides.csv` mechanism for correcting known-bad wiki rows.
- [ ] **Standing maintenance note** (not a blocking question): re-check for new combo_id
      collisions after every re-scrape (the scraper already warns about these) — most are
      expected ([data-model.md §6.1](data-model.md#61-character-buff-connection-羁绊-data)) but
      worth an eyeball each time in case a new one is a genuine data error
      like the one first suspected for 周瑜*小乔 (turned out correct on recheck, no override was
      needed).
- [x] ~~Confirm source of the master character roster~~ — done, then **corrected**:
      `load_master_roster()` in `utils/loader.py` originally derived it only from
      `data/buff_connections.csv` (~87 characters, missing anyone with zero 羁绊). Now unions
      that with the full roster from `data/characters.csv`
      ([data-model.md §6.2](data-model.md#62-players-owned-characters)), scraped separately via
      `scripts/scrape_characters.py`. Currently 119 characters.
- [x] ~~Decide exact local storage format/location for the `owned` flag file~~ — done, JSON at
      `data/owned_characters.json` (a plain array of owned character names), with
      `data/used_pairs.json` alongside it for
      [data-model.md §6.4](data-model.md#64-used-pair-tracking-achievement-progress), both
      gitignored as personal save-state. Implemented in `utils/loader.py`.
- [x] ~~Confirm granularity of "used" 羁绊 tracking~~ — row-level (`combo_id`, 目标, 天气) is the
      shipped and confirmed behavior
      ([data-model.md §6.4](data-model.md#64-used-pair-tracking-achievement-progress)), used
      throughout `utils/rules.py` (the `marked_score`
      / `new_progress_score` split depends on this granularity) with no issues raised in use.
      Closing as resolved; would only revisit if achievement-tracking against the real game
      reveals the wiki's own collection semantics are actually combo_id-only.
- [x] ~~Confirm whether multiple simultaneously-satisfied 羁绊 in one squad simply sum~~ — decided
      as the v1 working rule (implemented in `utils/rules.py::recommend_squads` — plain signed
      sum, no cap), open to revisiting once real gameplay use surfaces a case where it feels wrong.
      See [business-rules.md §8](business-rules.md#8-business-rules).
- [x] ~~Decide how debuff 羁绊 should surface in the UI~~ — the "⚠️ ... — 减益" label on each
      debuff-contributing 羁绊 (`pages/1_鸢报-突发情况.py`) is the shipped v1 treatment and is
      sufficient in practice. **Future enhancement, not blocking**: a dedicated banner if the
      *best available* squad still nets a debuff overall.
- [x] ~~Confirm whether non-buff character stats factor into scoring~~ — resolved as **no**: v1
      is confirmed 羁绊-synergy-only, no attack/defense/role/element data was ever sourced or
      modeled. Would only reopen if the game turns out to require stat thresholds for a Sudden
      Request to actually succeed (not just be recommended).
- [x] ~~Decide how to support multiple users on one deployed instance~~ — done: local
      username/password accounts via `streamlit-authenticator`
      (`utils/auth.py`/`scripts/manage_users.py`), chosen over Streamlit's native OIDC login
      (`st.login()`/Sign-in-with-Google) specifically to avoid requiring an externally-registered
      OAuth client — this app has no natural existing identity provider for its small
      friends/family user base. Per-user `owned`/`used_pairs` state moved from single shared JSON
      files to a SQLite database (`data/app.db`) keyed by username, since SQLite handles
      concurrent writers correctly and flat JSON files do not — see
      [data-model.md §6.5](data-model.md#65-authentication--multi-user-accounts).
- [x] ~~Decide whether the app should require an account at all~~ — done: added a "Continue as
      Guest" option alongside real login, backed by a random id stored in a browser cookie
      (persistent per-browser, chosen over a fully ephemeral session-only guest so a returning
      visitor doesn't lose their roster/progress) — see
      [data-model.md §6.5](data-model.md#65-authentication--multi-user-accounts). Guest ids use
      the exact same SQLite tables/code path as real usernames; the only accepted gap is no
      cleanup job for abandoned guest rows, deferred until usage data shows it matters.
- [x] ~~Fix identity-switch data corruption bug~~ — **found in real use**: log in as a real user,
      select characters, log out, log in as a guest (or a different user), make a different
      selection, log out, log back in as the first user — their original selection appeared lost.
      Root cause: `st.session_state.owned`/`used_pairs` (loaded once per browser session via
      `if "owned" not in st.session_state`) and per-character checkbox widget keys are not scoped
      to *who* is logged in — Streamlit's `session_state` persists across logins/logouts within
      the same browser tab. A later identity would silently reuse (and then re-save, overwriting)
      an earlier identity's in-memory selection. Fixed centrally in
      `utils/auth.py::require_login`/`_sync_identity`: on every call, compare the resolved
      `user_id` against a tracked `_active_user_id`; if it changed, wipe all session_state except
      a small identity-key allowlist (`authentication_status`, `username`, `name`, `guest_id`,
      etc.) and rerun, forcing every page to reload fresh from SQLite for the new identity. Fixing
      this also surfaced a related bug in the guest-mode addition above: checking
      `authentication_status` only after the silent `location="unrendered"` pre-check (not also
      after the interactive form call) meant a just-submitted valid login wasn't recognized until
      an extra rerun — fixed by checking after both calls (`_finish_real_login`). Verified with an
      end-to-end scripted repro of the exact reported scenario (real user → guest → same real
      user) confirming no cross-identity leakage.
- [x] ~~Let users create their own account instead of admin-only provisioning~~ — done: added a
      "📝 还没有账号？点击注册" expander to the login screen using streamlit-authenticator's
      built-in `register_user()` widget (`utils/auth.py`), alongside the existing
      `scripts/manage_users.py` admin CLI (kept for out-of-band account management). Captcha and
      the password-hint field are disabled for simplicity — this app has no email-sending
      configured anyway, so there's no functioning "forgot password" flow either way. Verified
      end-to-end: registering a new account via the form persists it into
      `.streamlit/auth_config.yaml` immediately (no extra save step, since the app already
      constructs `Authenticate` in file-path mode) and an immediate login with the new credentials
      succeeds, showing the correct display name in the sidebar.
- [x] ~~Fix "widget created with a default value but also had its value set via the Session
      State API" warning on 全选~~ — **found in real use**, `pages/2_角色管理.py`. Root cause:
      `st.checkbox(name, value=name in st.session_state.owned, key=key)` passed an explicit
      `value=True` for every character at the same time the 全选 (select-all) handler had just
      directly assigned `st.session_state[key] = True` for every character earlier in that same
      run — Streamlit warns whenever a widget's session-state key is freshly set via direct
      assignment *and* the widget call also passes a non-`False` `value=` in the same run (`False`
      is treated as "no real default," so 全部取消 alone never triggered it — only 全选). Fixed by
      dropping `value=` entirely from the checkbox call and instead seeding
      `st.session_state[key]` only the first time that key ever appears in a session; the
      select/deselect-all handlers' existing direct assignments are enough to drive the widget
      from then on. While verifying this, also found and fixed an adjacent staleness bug: the
      "已选择" `st.metric` was rendered *before* the select/deselect-all handler updated
      `st.session_state.owned`, so it displayed the pre-click count for one rerun even though the
      checkboxes below already showed the post-click state — fixed by moving the metric render to
      after the handler block. Verified with a scripted click of both buttons confirming the
      counter updates immediately and no warning banner appears.
- [x] ~~Make the app deployable to a free host~~ — done: added `utils/bootstrap.py`, called from
      `require_login()` on every page. Re-fetches gitignored image assets
      (`scripts/scrape_characters.py`/`scripts/download_weather_icons.py`, run via `subprocess`)
      if `assets/characters`/`assets/weather` are empty, and restores `.streamlit/auth_config.yaml`
      from a Streamlit secret if that file is missing — both guarded by `st.cache_resource` so the
      check only actually does work once per running server process. Chose "auto re-fetch on cold
      start" over committing assets to the repo (would need a private repo and still sits at odds
      with the existing copyright note on scraped game art), and "bootstrap from a secret" over
      committing real credentials to git for the same reason. Explicitly *not* solved: `data/app.db`
      has no equivalent bootstrap/backup, so a redeploy still loses all saved
      characters/progress — accepted as out of scope for now, see
      [§11](#11-constraints). Verified end-to-end: with `assets/`
      present and `auth_config.yaml` temporarily moved aside plus a matching Streamlit secret in
      place, a fresh app start correctly recreated the file from the secret and logged in
      successfully; with everything present as normal, the bootstrap checks are a verified no-op
      (existing local dev environment unaffected).
- [x] ~~Pre-deploy readiness check~~ — done: confirmed a clean `pip install -r requirements.txt`
      into a brand-new venv (matching what a fresh deploy container does) resolves with no
      conflicts, and cross-checked every `import` in the codebase against `requirements.txt` -
      added `PyYAML` explicitly (`scripts/manage_users.py` imports it directly, but it was only
      present as a transitive dependency of `streamlit-authenticator`, which is fragile). Ran the
      app from that clean venv and walked through the first-time-visitor path end to end (login
      screen → guest login → landing page → 鸢报-突发情况 with an empty roster → 角色管理 →
      selecting characters → back to a real recommendation result) with no console errors. Found
      and fixed one real issue: the login form itself (`Login`/`Username`/`Password`/`Login`
      button) was still in English by default while every other screen in the app is Chinese -
      `utils/auth.py` now passes a `fields=` dict to both `authenticator.login()` calls and a
      Chinese `password_instructions` string to `Authenticate(...)`, so the whole login/register
      screen is consistently Chinese.
