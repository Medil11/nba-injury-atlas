# nba-injury-atlas

**Where do NBA players get hurt, and what does it cost?** Two animated GIFs and three [marimo](https://marimo.io) dashboards built from injured-list placements, game logs and salaries (the first GIF covers seasons 2018-19 to 2022-23, the second 2010-11 to 2022-23).

![GIF](body_map.gif)

The GIF (720 × 900, ~26 s, ~10 MB) chains four scenes:

1. **Where do NBA players get hurt?** Front and back silhouettes, body zones coloured by cumulative days missed, with the number of injuries and an example player (longest absence) for each zone.
2. **Torn ACLs.** One bar per tear, from the placement on the injured list to the first game played.
3. **The knee, the costliest injury.** Salaries paid during knee-injury absences.
4. **The 3 most injured franchises** since 2010-11 (cumulative days missed), with team logos.

### The most common injuries

![Injury types](injury_types.gif)

The second GIF (720 × 900, ~22 s, ~2.5 MB) chains three scenes:

1. **The most common NBA injuries.** Top 10 injury types (nature + body part, e.g. "Ankle sprain"), with the average days out.
2. **What kind of injuries?** A waffle chart of the nature of each injury (soreness, sprain, strain, bruise, fracture, tear, concussion).
3. **Common is not serious.** The most frequent injury against the one with the longest absences among frequent injuries.

## Results (at generation time)

| | |
|---|---|
| Injuries with a known body part | 3,480 of 5,072 injured-list placements, Sep 2018 – Apr 2023 |
| Knee | ≈ $753M in salaries, 13,835 days missed (costliest body part) |
| Torn ACLs | 13 tears, ≈ $128M, 0.5% of injuries but 4.3% of days missed |
| Franchises (2010-11 → 2022-23) | Warriors 4,156 days, Bucks 4,047, Nets 4,029: **a very tight podium** |
| Most common injury (2010-11 → 2022-23) | Ankle sprain: 806 of 6,352 injuries with a known body part (12.7%), 11 days out on average; then knee soreness (484) and lower back soreness (307) |
| Soft tissue vs structural | Soreness, sprains, strains and bruises: 80% of injuries that state their nature. Knee tears: 110 cases, 73 days out on average, 89% as many days missed as ankle sprains |

## Files

| File | Role |
|---|---|
| `make_gif.py` | Builds `body_map.gif` (Pillow, assembled with the [slack-gif-creator](https://skills.sh/anthropics/skills/slack-gif-creator) toolkit) |
| `make_types_gif.py` | Builds `injury_types.gif` (reuses the helpers of `make_gif.py`) |
| `injury_types.py` | Reads the nature of each injury (sprain, strain...) and ranks injury types |
| `nba_injury_types.py` | marimo dashboard: most common injuries by season, nature, number / days missed |
| `bodymap.py` | Cleans injury notes, maps them to body parts, computes absence days, franchise ranking, body shapes |
| `prep.py` | Player-season table: salary, games missed, cost (used by the dashboard) |
| `nba_injuries.py` | marimo dashboard: cost of absences by franchise, season, player |
| `nba_body_map.py` | marimo dashboard: interactive body map |
| `fetch_games.py` | Downloads game logs (`nba_api`) |

## Setup

```bash
pip install -r requirements.txt
npx skills add anthropics/skills@slack-gif-creator -g -y   # GIF utilities (GIFBuilder, easing) used by make_gif.py
```

`make_gif.py` uses Windows fonts (`C:/Windows/Fonts`: Rockwell Extra Bold, Arial). On another system, adapt `FONTS`, `SLAB`, `BOLD`, `REG`.

## Data (not in the repo: the `data/` folder is git-ignored)

- **Injuries:** Kaggle dataset [`loganlauton/nba-injury-stats-1951-2023`](https://www.kaggle.com/datasets/loganlauton/nba-injury-stats-1951-2023) (from Pro Sports Transactions), up to April 2023. Save it as `data/injuries_kaggle.csv`. Check its license.
  ```python
  import kagglehub; print(kagglehub.dataset_download("loganlauton/nba-injury-stats-1951-2023"))
  ```
- **Game logs:** `python fetch_games.py` creates `data/player_games_*.csv` and `data/team_games_*.csv` (2010-11 to 2022-23).
- **Salaries:** one file per season, `data/salaries_<start year>.csv` (2018 to 2022 for the GIF), with columns `team` (e.g. `boston-celtics`), `season`, `player_id`, `player`, `salary`, `cap_hit`, `two_way`, `terminated`. They were collected from HoopsHype team pages and are not redistributed here. Check the site's terms before reusing that data.
- **Photos and logos:** downloaded automatically the first time `make_gif.py` runs: player headshots from nba.com (cached in `data/headshots/`), team logos from ESPN's CDN (cached in `data/logos/`). These images are copyrighted and trademarked: do not republish the GIF without checking the rights.

## Usage

```bash
python fetch_games.py                       # once
python make_gif.py                          # -> body_map.gif (~2 min)
python -m marimo run nba_injuries.py        # cost-of-absences dashboard
python -m marimo run nba_body_map.py        # interactive body map
python make_types_gif.py                    # -> injury_types.gif (~1.5 min)
python -m marimo run nba_injury_types.py    # most common injuries
```

## Method and limits

- **Absence:** days between the placement on the injured list and the earlier of the player's next transaction or his first game played afterwards (the dataset misses some returns; without capping at the first game played, the knee cost was overestimated by about 7%). Mid-April if neither exists.
- **Cost:** season salary pro-rated over the days spent on the injured list during the regular season (Oct 20 – Apr 12). This is an **estimate**, more likely a floor: absences never declared on the list are not counted.
- **Body part:** keyword matching on the notes ("sprained left ankle"). Left and right are pooled. 1,592 placements have no detail or are illnesses / COVID protocols, so they are not located.
- **Injury type:** the nature is read from the note by keywords (sprain, strain, soreness / spasms, bruise, fracture, tear...). 1,732 of the 6,352 located injuries (27%) only say "knee injury", "hamstring injury"... : they count in the shares but not in the ranking, so the real ranking could differ (many unspecified hamstring or ankle injuries are probably strains or sprains). "Soreness" includes tightness, spasms and cramps. "Knee tear" pools ACL and meniscus tears. A type is counted per injured-list placement, not per player.
- **Torn ACLs:** only 13 distinct tears in the data (many absences never go through the injured list). The return is the first game played, because the dataset's "activated from IL" dates are sometimes wrong or missing.
- **Franchise ranking:** fragile. The top 5 are within 4% of each other, and the top 3 changes with the period or scope (all injuries: Nets, Warriors, 76ers). It measures declared injured-list stints, not every absence. Bobcats = Hornets; "Hornets" before July 2013 = Pelicans.
- **Silhouette:** a hand-drawn human outline (curves), not an anatomical illustration.
