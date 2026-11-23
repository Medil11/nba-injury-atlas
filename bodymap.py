"""Where NBA players get hurt: injury notes (Kaggle / Pro Sports Transactions) -> body part -> SVG body map.

Days of absence = calendar days from "placed on the injured list" to the player's next transaction or, if
earlier, his first game played afterwards (the dataset misses some returns); mid-April if neither exists.
Left/right is ignored: both sides are pooled into one body part.
"""
import glob
import re

import numpy as np
import pandas as pd

from prep import norm

# first matching rule wins; None = not a body part (illness, covid protocols...)
RULES = [
    (None, r"illness|covid|health and safety|protocol|\bflu\b|virus|sick|sore throat|personal|suspension|conditioning|ineligible|\brest\b|non-injury|strep|pneumonia|gastro|nausea|respiratory|bronch|infection|dental|dehydr|quarantine|medical test|fatigue|heartbeat|vestibular|sinus"),
    ("achilles", r"achilles"),
    ("hamstring", r"hamstring"),
    ("neck", r"\bneck\b|cervical"),
    ("head", r"concussion|\bhead|facial|\bface\b|\bnose|\beye|\bjaw|skull|orbital|\bear\b|mouth|tooth|teeth|cheek|\bchin\b|\blip\b"),
    ("shoulder", r"shoulder|clavicle|collarbone|rotator|acromio|scapula"),
    ("chest", r"\bchest|\bribs?\b|pectoral|sternum"),
    ("abdomen", r"abdom|oblique|\bcore\b|stomach|hernia|append|\bside\b"),
    ("upper_back", r"thoracic|upper back|trapez"),
    ("lower_back", r"\bback\b|spine|spinal|lumbar|\bdisc\b|\bdisk\b|sacr|tailbone|coccyx"),
    ("hip", r"\bhip|pelvi|glute|groin|adductor"),
    ("knee", r"\bknee|\bacl\b|\bmcl\b|\blcl\b|\bpcl\b|menisc|patell|kneecap"),
    ("quad", r"quad|thigh"),
    ("calf", r"calf|soleus|gastrocnem"),
    ("shin", r"\bshin|tibia|fibula|lower leg|\bleg\b"),
    ("ankle", r"ankle"),
    ("foot", r"\bfoot|\bfeet\b|\btoes?\b|heel|plantar|metatars|navicular|sesamoid|\barch\b"),
    ("arm", r"elbow|bicep|tricep|forearm|\barm\b|humer|\bulna|\bradius"),
    ("hand", r"wrist|\bhand\b|finger|thumb|knuckle|\bpalm\b"),
]
LABEL = {
    "head": "Head / face", "neck": "Neck", "shoulder": "Shoulder", "chest": "Chest / ribs",
    "abdomen": "Abdomen / obliques", "upper_back": "Upper back", "lower_back": "Lower back",
    "hip": "Hip / groin", "arm": "Arm / elbow", "hand": "Hand / wrist", "quad": "Thigh",
    "hamstring": "Hamstring", "knee": "Knee", "shin": "Shin / lower leg", "calf": "Calf",
    "achilles": "Achilles tendon", "ankle": "Ankle", "foot": "Foot / toes",
}
SEASONS = range(2018, 2023)  # Kaggle injury data ends 2023-04


def region(note):
    detail = re.sub(r"^placed on il\s*", "", str(note).lower())
    for name, pat in RULES:
        if re.search(pat, detail):
            return name or "non-body"
    return "unknown"


def injuries(seasons=SEASONS, path="data/injuries_kaggle.csv"):
    """One row per placement on the injured list: season, player, team, region, days, note, placed, end."""
    k = pd.read_csv(path, parse_dates=["Date"])
    k = k[k.Date >= f"{min(seasons)}-07-01"].copy()
    k["season"] = k.Date.dt.year - (k.Date.dt.month < 7)
    k["player"] = k.Relinquished.fillna(k.Acquired)
    k = k[k.season.isin(seasons) & k.player.notna()].sort_values("Date")
    pl = pd.concat(pd.read_csv(f, usecols=["PLAYER_NAME", "GAME_DATE"]) for y in seasons for f in glob.glob(f"data/player_games_{y}-*.csv"))
    played = {n: np.sort(x.to_numpy()) for n, x in pd.to_datetime(pl.GAME_DATE).groupby(pl.PLAYER_NAME.map(norm))}
    rows = []
    for (season, _), g in k.groupby(["season", "player"]):
        d, notes, rel = list(g.Date), list(g.Notes), list(g.Relinquished.notna())
        for i, n in enumerate(notes):
            if rel[i] and str(n).lower().startswith("placed on il"):
                end = d[i + 1] if i + 1 < len(d) else pd.Timestamp(f"{season + 1}-04-15")
                games = played.get(norm(g.player.iloc[i]), [])
                j = np.searchsorted(games, d[i].to_datetime64(), side="right") if len(games) else 0
                if j < len(games):  # he played again: the absence is over, whatever the dataset says
                    end = min(end, pd.Timestamp(games[j]))
                rows.append((season, g.player.iloc[i], g.Team.iloc[i], region(n), max((end - d[i]).days, 0), str(n).lower(), d[i], end))
    return pd.DataFrame(rows, columns=["season", "player", "team", "region", "days", "note", "placed", "end"])


FULL = {  # injury-data nickname -> franchise name
    "Hawks": "Atlanta Hawks", "Celtics": "Boston Celtics", "Nets": "Brooklyn Nets", "Hornets": "Charlotte Hornets", "Bulls": "Chicago Bulls",
    "Cavaliers": "Cleveland Cavaliers", "Mavericks": "Dallas Mavericks", "Nuggets": "Denver Nuggets", "Pistons": "Detroit Pistons",
    "Warriors": "Golden State Warriors", "Rockets": "Houston Rockets", "Pacers": "Indiana Pacers", "Clippers": "LA Clippers",
    "Lakers": "Los Angeles Lakers", "Grizzlies": "Memphis Grizzlies", "Heat": "Miami Heat", "Bucks": "Milwaukee Bucks",
    "Timberwolves": "Minnesota Timberwolves", "Pelicans": "New Orleans Pelicans", "Knicks": "New York Knicks", "Thunder": "Oklahoma City Thunder",
    "Magic": "Orlando Magic", "76ers": "Philadelphia 76ers", "Suns": "Phoenix Suns", "Blazers": "Portland Trail Blazers", "Kings": "Sacramento Kings",
    "Spurs": "San Antonio Spurs", "Raptors": "Toronto Raptors", "Jazz": "Utah Jazz", "Wizards": "Washington Wizards",
}


def franchise(team, date):
    """Current nickname of the franchise: Bobcats -> Hornets; 'Hornets' before July 2013 is New Orleans -> Pelicans."""
    if team == "Bobcats":
        return "Hornets"
    return "Pelicans" if team == "Hornets" and date < pd.Timestamp("2013-07-01") else team


def by_franchise(inj):
    """Franchise ranking: cumulated days of absence and number of injuries, only injuries whose body part is known
    (as in the body map: leaves out illness, COVID protocols and the many placements with no detail)."""
    d = inj[inj.region.isin(LABEL)].copy()
    d["franchise"] = [franchise(t, p) for t, p in zip(d.team, d.placed)]
    t = d.groupby("franchise").days.agg(days="sum", injuries="size").sort_values("days", ascending=False).reset_index()
    t["name"] = t.franchise.map(FULL)
    return t


def by_region(inj):
    """Body-part table: injuries, cumulated days, average days."""
    t = inj[inj.region.isin(LABEL)].groupby("region").days.agg(injuries="size", days="sum").reset_index()
    t["avg_days"] = (t.days / t.injuries).round(1)
    t["label"] = t.region.map(LABEL)
    return t.sort_values("days", ascending=False).reset_index(drop=True)


# ---- body shapes, in a 200 x 415 box; ("e", cx, cy, rx, ry) ellipse, ("r", x, y, w, h, radius) rect.
def _pair(cx, cy, rx, ry):
    return [("e", cx, cy, rx, ry), ("e", 200 - cx, cy, rx, ry)]


SHAPES = {
    "head": [("e", 100, 30, 17, 22)],
    "neck": [("r", 91, 50, 18, 16, 5)],
    "shoulder": _pair(66, 76, 15, 12),
    "arm": _pair(50, 116, 10, 34) + _pair(44, 178, 9, 30),
    "hand": _pair(40, 222, 9, 13),
    "hip": [("r", 70, 158, 60, 26, 12)],
    "ankle": _pair(80, 376, 9, 9),
    "foot": _pair(78, 398, 13, 8),
}
FRONT = {
    **SHAPES,
    "chest": [("r", 72, 68, 56, 44, 12)], "abdomen": [("r", 74, 112, 52, 46, 10)],
    "quad": _pair(84, 232, 17, 46), "knee": _pair(84, 290, 13, 13), "shin": _pair(82, 332, 11, 30),
}
BACK = {
    **SHAPES,
    "upper_back": [("r", 72, 68, 56, 44, 12)], "lower_back": [("r", 74, 112, 52, 46, 10)],
    "hamstring": _pair(84, 232, 17, 46), "calf": _pair(82, 332, 11, 30), "achilles": [("r", 76, 358, 8, 14, 3), ("r", 116, 358, 8, 14, 3)],
}
LABEL_AT = {  # where the value label goes (one per region)
    "head": (100, 30), "neck": (100, 59), "shoulder": (66, 76), "arm": (50, 116), "hand": (40, 222), "hip": (100, 171),
    "ankle": (80, 376), "foot": (78, 398), "chest": (100, 90), "abdomen": (100, 135), "quad": (84, 232), "knee": (84, 290),
    "shin": (82, 332), "upper_back": (100, 90), "lower_back": (100, 135), "hamstring": (84, 232), "calf": (82, 332),
    "achilles": (80, 365),
}
LIGHT, DARK, SURFACE, EMPTY = (243, 233, 214), (164, 22, 26), "#e8e5da", "#f1eee4"


def _color(v, vmax):
    t = (v / vmax) ** 0.6 if vmax else 0  # sqrt-ish so mid values stay readable
    return "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(LIGHT, DARK))


def _shape(s, fill, title):
    if s[0] == "e":
        g = f'<ellipse cx="{s[1]}" cy="{s[2]}" rx="{s[3]}" ry="{s[4]}"'
    else:
        g = f'<rect x="{s[1]}" y="{s[2]}" width="{s[3]}" height="{s[4]}" rx="{s[5]}"'
    return f'{g} fill="{fill}" stroke="#3b3b38" stroke-width="1.3"><title>{title}</title>' + ("</ellipse>" if s[0] == "e" else "</rect>")


def svg(tab, metric="days", title="Where do NBA players get hurt?", subtitle="", footer=""):
    """Poster-style SVG (720 x 900): front and back figures coloured by `metric` ('days' or 'injuries')."""
    vals = dict(zip(tab.region, tab[metric]))
    vmax = max(vals.values(), default=0)
    unit = "days missed" if metric == "days" else "injuries"
    figs, labelled = [], set()
    top = set(sorted(vals, key=vals.get, reverse=True)[:6])
    for ox, shapes, view in ((30, FRONT, "front"), (370, BACK, "back")):
        parts = []
        for reg, items in shapes.items():
            v = vals.get(reg, 0)
            row = tab[tab.region == reg]
            tip = f"{LABEL[reg]}: {v:,.0f} {unit}"
            if len(row):
                tip += f" · {int(row.injuries.iloc[0])} injuries, {row.avg_days.iloc[0]} days on average"
            parts += [_shape(s, _color(v, vmax) if v else EMPTY, tip) for s in items]
        for reg in shapes:
            if reg in top and reg not in labelled:
                x, y = LABEL_AT[reg]
                labelled.add(reg)
                parts.append(f'<text x="{x}" y="{y + 3}" text-anchor="middle" font-size="9" font-weight="700" fill="#1b1b1a" '
                             f'stroke="#fff" stroke-width="2.6" paint-order="stroke">{vals[reg]:,.0f}</text>')
        figs.append(f'<g transform="translate({ox},130) scale(1.6)">{"".join(parts)}</g>')
    ramp = "".join(f'<rect x="{250 + i * 22}" y="826" width="22" height="12" fill="{_color(i, 9)}"/>' for i in range(10))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 900" width="720" height="900" font-family="Arvo, Rockwell, \'Roboto Slab\', Georgia, serif">'
        f'<rect width="720" height="900" fill="{SURFACE}"/>'
        f'<text x="360" y="62" text-anchor="middle" font-size="34" font-weight="800" fill="#1b1b1a">{title}</text>'
        f'<text x="360" y="94" text-anchor="middle" font-size="17" font-weight="700" fill="#6b6b66" font-family="Helvetica, Arial, sans-serif">{subtitle}</text>'
        f'{"".join(figs)}{ramp}'
        f'<text x="240" y="837" text-anchor="end" font-size="12" fill="#6b6b66" font-family="Helvetica, Arial, sans-serif">less</text>'
        f'<text x="480" y="837" font-size="12" fill="#6b6b66" font-family="Helvetica, Arial, sans-serif">more {unit}</text>'
        f'<text x="360" y="864" text-anchor="middle" font-size="13" font-weight="700" fill="#6b6b66" font-family="Helvetica, Arial, sans-serif">{footer}</text>'
        f'<text x="360" y="884" text-anchor="middle" font-size="12" fill="#6b6b66" font-family="Helvetica, Arial, sans-serif">source: Pro Sports Transactions (via Kaggle) · left and right pooled</text>'
        f'</svg>'
    )


def poster(inj, metric="days"):
    tab = by_region(inj)
    placed, located = len(inj), int(tab.injuries.sum())
    lo = f"{inj.season.min()}-{str(inj.season.min() + 1)[2:]}"
    sub = f"{located:,} injuries since {lo} · color = {'cumulative days missed' if metric == 'days' else 'number of injuries'}"
    foot = f"{located:,} of {placed:,} injured-list placements have a known body part"
    return svg(tab, metric, subtitle=sub, footer=foot)


if __name__ == "__main__":
    inj = injuries()
    assert (inj.days >= 0).all()
    print(inj.region.value_counts().head(8).to_string())
    print(by_region(inj).to_string())
    print("placements:", len(inj), "| located:", int(by_region(inj).injuries.sum()))
    open("body_map.svg", "w", encoding="utf-8").write(poster(inj))
    print("wrote body_map.svg")
