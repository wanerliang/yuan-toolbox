# 🎮 如鸢 Team Optimizer

> **Note**: this project is a purely vibe-coded personal experiment — built for fun/learning, not
> production-grade software. Expect rough edges.

A Streamlit web app that recommends the best 3–5 character squad for 鸢报-突发情况 (Sudden Request)
quests in 如鸢 (Ru Yuan), based on scraped 羁绊 (buff-connection) data from the community wiki.

📋 See [BUSINESS_REQUIREMENTS.md](BUSINESS_REQUIREMENTS.md) for the full context, rules, and open questions — read that first before making changes.

## 🚀 Run Locally

```bash
pip install -r requirements.txt
python scripts/scrape_buff_connections.py   # first run only, or after a game update
python scripts/scrape_characters.py         # first run only, or after a game update
python scripts/download_weather_icons.py    # first run only, or if the wiki changes icons
streamlit run app.py
```

`data/buff_connections.csv` and `data/characters.csv` are committed to the repo, so you can skip
straight to `streamlit run app.py` on a normal clone. **`assets/characters/` and `assets/weather/`
are gitignored** (see [Copyright note](#️-copyright-note-on-scraped-assets) below) — run the two
scraper commands above once to (re)populate them locally before first launch.

`app.py` is a landing page with links to the two tools; use the left-hand page nav to switch
between them directly (🎯 鸢报-突发情况 for recommendations, 👥 角色管理 for roster/ownership).

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
├── BUSINESS_REQUIREMENTS.md            # Source of truth for scope/rules — read first
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml                     # App theme and server settings
├── pages/
│   ├── 1_鸢报-突发情况.py               # Squad recommendation tool (formerly app.py's content)
│   └── 2_角色管理.py                    # Character ownership management (search, select all/none, avatars)
├── scripts/
│   ├── scrape_buff_connections.py      # Wiki -> data/buff_connections.csv (run manually on game updates)
│   ├── scrape_characters.py            # Wiki -> data/characters.csv + assets/characters/*.png
│   └── download_weather_icons.py       # Wiki -> assets/weather/*.png (run manually if icons change)
├── assets/                             # gitignored - regenerate via the scripts above
│   ├── weather/                        # Locally-cached 天气 icon images (8 PNGs)
│   └── characters/                     # Locally-cached character avatar images (119 PNGs)
├── data/
│   ├── buff_connections.csv            # Generated 羁绊 data, committed (do not hand-edit — use overrides instead)
│   ├── buff_connections_overrides.csv  # Manual corrections for known-bad wiki rows, committed
│   ├── characters.csv                  # Full character roster (name + local avatar path), committed
│   ├── owned_characters.json           # gitignored - personal "which characters do I own" state
│   └── used_pairs.json                 # gitignored - personal "which 羁绊 have I already triggered" state
└── utils/
    ├── constants.py                    # 目标 / 天气 / squad-size options
    ├── loader.py                       # Data loading + local-state persistence
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

**Important**: this app was designed as a **single-user local tool** (see
[BUSINESS_REQUIREMENTS.md](BUSINESS_REQUIREMENTS.md) §4/§5/§11) — "owned characters" and "used
羁绊" state is stored in two plain JSON files (`data/owned_characters.json`,
`data/used_pairs.json`), shared by whoever is running the app. If you deploy this to a **public**
URL (e.g. Streamlit Community Cloud), **every visitor shares and can overwrite the same state** —
there's no per-user accounts or isolation. Fine for a private/personal deployment only you access;
not fine as a public multi-user app without further work.

To deploy anyway (e.g. for your own personal use from multiple devices):

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo.
3. Since `assets/` is gitignored, add a build step (or a one-time setup command) that runs
   `scripts/scrape_characters.py` and `scripts/download_weather_icons.py` before the app starts —
   otherwise avatars/weather icons won't render on the deployed instance.
