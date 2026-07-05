# 🎮 如鸢 Team Optimizer

> **Note**: this project is a purely vibe-coded personal experiment — built for fun/learning, not
> production-grade software. Expect rough edges.

A Streamlit web app that recommends the best 3–5 character squad for 鸢报-突发情况 (Sudden Request)
quests in 如鸢 (Ru Yuan), based on scraped 羁绊 (buff-connection) data from the community wiki.

📋 See [CLAUDE.md](CLAUDE.md) for the full context, rules, and open questions (split across `docs/` by concern) — read that first before making changes.

## 🚀 Run Locally

```bash
pip install -r requirements.txt
python scripts/scrape_buff_connections.py   # first run only, or after a game update
python scripts/scrape_characters.py         # first run only, or after a game update
python scripts/download_weather_icons.py    # first run only, or if the wiki changes icons
cp .streamlit/auth_config.yaml.example .streamlit/auth_config.yaml
python scripts/manage_users.py add <username> "<display name>"   # add at least one login account
streamlit run app.py
```

`data/buff_connections.csv` and `data/characters.csv` are committed to the repo, so you can skip
straight to the auth/login setup on a normal clone. **`assets/characters/` and `assets/weather/`
are gitignored** (see [Copyright note](#️-copyright-note-on-scraped-assets) below) — run the two
scraper commands above once to (re)populate them locally before first launch.

The app requires logging in (see [Multi-User Accounts](#-multi-user-accounts) below) — every page
is gated behind a username/password check, and each account has its own owned-character selection
and 羁绊 collection progress.

`app.py` is a landing page with links to the two tools; use the left-hand page nav to switch
between them directly (🎯 鸢报-突发情况 for recommendations, 👥 角色管理 for roster/ownership).

## 👤 Multi-User Accounts

The app supports multiple independent logins against one running instance — each account gets
its own owned-character selection and 羁绊 collection progress (stored in a local SQLite database,
`data/app.db`, keyed by username). Login uses local username/password accounts
(`streamlit-authenticator`), not a third-party identity provider — no OAuth app to register.

```bash
python scripts/manage_users.py add alice "Alice"     # prompts for a password
python scripts/manage_users.py list
python scripts/manage_users.py remove alice
```

This edits `.streamlit/auth_config.yaml` (gitignored — contains bcrypt password hashes and a
cookie-signing secret; copy `.streamlit/auth_config.yaml.example` to create it the first time).

**Users can also register themselves**: the login screen has a "📝 还没有账号？点击注册"
(Register) expander where anyone can create their own account (name, email, username, password) —
no admin step required. It writes straight into `.streamlit/auth_config.yaml`, same file the CLI
above manages, so both approaches work together (e.g. use the CLI for accounts you want to
provision ahead of time, and leave self-registration open for everyone else).

**No account needed**: the login screen also has a "以访客身份继续" (Continue as Guest) button.
Guests get a random id stored in a browser cookie, so their owned-character selection and 羁绊
progress persist across visits *from that same browser* without ever registering — a different
browser, or clearing cookies, starts a brand-new unrelated guest identity. "退出访客模式" ends
that guest identity for good.

If you have existing single-user save data from before this change
(`data/owned_characters.json`/`data/used_pairs.json`), migrate it to a specific account once with:

```bash
python scripts/migrate_json_to_db.py <username>
```

## 🔄 Updating 羁绊 Data

The app reads `data/buff_connections.csv`, which is generated from the wiki, not entered by hand.
Re-run this after a game update adds/changes characters or 羁绊:

```bash
python scripts/scrape_buff_connections.py
```

Known-bad wiki rows can be corrected without re-editing the generated CSV by adding a row to
`data/buff_connections_overrides.csv` (`action` = `override` to fix a value, or `exclude` to drop
a spurious row) — the scraper re-applies it on every run.

## 🌤️ Updating Weather Icons

The 天气 picker shows icons downloaded once from the same wiki page into `assets/weather/`, so
the app has no runtime dependency on the wiki being reachable. Only needs re-running if the wiki
changes these icons:

```bash
python scripts/download_weather_icons.py
```

## 👥 Updating the Character Roster

The 角色管理 page's roster (name + avatar) comes from `data/characters.csv` / `assets/characters/`,
scraped from the wiki's **密探** (Secret Agent) category page — this is the *full* character list
(119 as of this writing), including characters with zero 羁绊, unlike deriving the roster from
`buff_connections.csv` alone (~87). Re-run after a game update adds characters:

```bash
python scripts/scrape_characters.py
```

Note: the wiki's query API rate-limits repeated calls in quick succession, so this script fetches
everything in one request rather than paginating — see the script's docstring if it ever needs
revisiting.

## 📁 Project Structure

```
yuan/
├── app.py                              # Landing page - links to the pages below
├── requirements.txt                    # Python dependencies
├── runtime.txt                         # Pinned Python version for deployment platforms
├── LICENSE                             # MIT (code only - see copyright note below)
├── BUSINESS_REQUIREMENTS.md            # Pointer into docs/ — read CLAUDE.md first for the index
├── CLAUDE.md                           # Index of docs/ split by concern, for humans and coding agents
├── docs/                               # Full requirements, split by concern (see CLAUDE.md)
├── README.md
├── .gitignore
├── .streamlit/
│   ├── config.toml                     # App theme and server settings
│   └── auth_config.yaml.example        # Template for auth_config.yaml (gitignored - see below)
├── pages/
│   ├── 1_鸢报-突发情况.py               # Squad recommendation tool (formerly app.py's content)
│   └── 2_角色管理.py                    # Character ownership management (search, select all/none, avatars)
├── scripts/
│   ├── scrape_buff_connections.py      # Wiki -> data/buff_connections.csv (run manually on game updates)
│   ├── scrape_characters.py            # Wiki -> data/characters.csv + assets/characters/*.png
│   ├── download_weather_icons.py       # Wiki -> assets/weather/*.png (run manually if icons change)
│   ├── manage_users.py                 # Admin CLI: add/remove/list login accounts
│   └── migrate_json_to_db.py           # One-off: import old single-user JSON state into SQLite for a user
├── assets/                             # gitignored - regenerate via the scripts above
│   ├── weather/                        # Locally-cached 天气 icon images (8 PNGs)
│   └── characters/                     # Locally-cached character avatar images (119 PNGs)
├── data/
│   ├── buff_connections.csv            # Generated 羁绊 data, committed (do not hand-edit — use overrides instead)
│   ├── buff_connections_overrides.csv  # Manual corrections for known-bad wiki rows, committed
│   ├── characters.csv                  # Full character roster (name + local avatar path), committed
│   └── app.db                          # gitignored - per-user owned/used-pair state (SQLite)
└── utils/
    ├── constants.py                    # 目标 / 天气 / squad-size options
    ├── loader.py                       # Shared reference data loading (buff/character CSVs)
    ├── db.py                           # Per-user SQLite persistence (owned characters, used pairs)
    ├── auth.py                         # Login gate (require_login()), used by every page
    ├── bootstrap.py                    # Fresh-deploy bootstrap: re-fetch assets, restore auth config from secret
    └── rules.py                        # Squad scoring/recommendation logic
```

## ⚠️ Copyright Note on Scraped Assets

Character portraits and weather icons in `assets/` are the game publisher's copyrighted art,
scraped from the community wiki for personal local use — not this project's to redistribute.
They're **gitignored** and regenerated locally via `scripts/scrape_characters.py` and
`scripts/download_weather_icons.py`. `data/buff_connections.csv` and `data/characters.csv` are
structured gameplay data (character names, bond values, image *URLs*) rather than the art itself,
and are committed to the repo so the app runs immediately after cloning without hitting the wiki.

## ☁️ Deploy

The app supports **multiple independent users** against one deployed instance — see
[Multi-User Accounts](#-multi-user-accounts) above. Each logged-in account's owned-character
selection and 羁绊 progress is isolated in `data/app.db`, keyed by username; only the login
accounts themselves (`.streamlit/auth_config.yaml`) and the SQLite file are per-deployment state,
not shared reference data.

**Important caveat**: most free hosts (including Streamlit Community Cloud) reset the app's local
disk to match the GitHub repo on every redeploy (i.e. every time you push a code change) — it
survives simple sleep/wake in between, just not a rebuild. `data/app.db` (everyone's saved
characters/progress) has no protection against this; treat that as an accepted trade-off for a
small free deployment, not something this project currently solves. The two other pieces of
local-only state — asset images and login accounts — *do* have a fix, described below.

To deploy to **Streamlit Community Cloud**:

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo.
3. **Avatars/weather icons**: nothing to do — `utils/bootstrap.py::ensure_assets()` detects that
   `assets/characters/`/`assets/weather/` are empty on a fresh deploy (they're gitignored, see the
   copyright note above) and automatically runs `scripts/scrape_characters.py` +
   `scripts/download_weather_icons.py` once, the first time any page loads. Takes a little longer
   on that first request only.
4. **Login accounts**: `.streamlit/auth_config.yaml` is also gitignored (bcrypt hashes + a cookie
   secret), so a fresh deploy starts with zero accounts unless you provide one. In the Community
   Cloud app's **Settings → Secrets**, add:
   ```toml
   auth_config_yaml = """
   <paste the full contents of your local .streamlit/auth_config.yaml here>
   """
   ```
   `utils/bootstrap.py::ensure_auth_config()` writes this out to `.streamlit/auth_config.yaml` on
   first load if that file doesn't already exist. Note this is a one-way bootstrap: accounts
   created later (via self-registration or `manage_users.py`) only live in that deployment until
   the next redeploy — copy the file's current contents back into the secret afterward if you want
   to keep them.
