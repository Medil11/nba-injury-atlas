"""Build the player-season table: salary, games missed, cost of missed games, IL-attributed games.

Cost of a missed game = salary / team games. "Missed" = team games in the player's window
minus games played (any reason: injury, rest, suspension). "missed_il" = team games spent
on the injured list, from the Kaggle injury data (Pro Sports Transactions).
"""
import difflib
import glob
import re
import unicodedata

import pandas as pd

D = "data"
SEASONS = range(2018, 2023)  # start years; Kaggle injury data ends 2023-04
NICK_FIX = {"sixers": "76ers"}  # injury-data nickname -> NBA nickname


def norm(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    parts = re.sub(r"[^a-z ]", "", s).split()
    if parts and parts[-1] in ("jr", "sr", "ii", "iii", "iv"):
        parts = parts[:-1]
    return "".join(parts)


def tkey(team):
    k = str(team).lower().split()[-1]
    return NICK_FIX.get(k, k)


def _read(pattern, cols):
    files = [f for y in SEASONS for f in glob.glob(f"{D}/{pattern}_{y}-*.csv")]
    df = pd.concat(pd.read_csv(f, usecols=cols) for f in files)
    df["season"] = df.SEASON_YEAR.str[:4].astype(int)
    df["date"] = pd.to_datetime(df.GAME_DATE)
    df["tkey"] = df.TEAM_NAME.map(tkey)
    return df


def build():
    pg = _read("player_games", ["SEASON_YEAR", "PLAYER_NAME", "TEAM_NAME", "GAME_DATE"])
    tg = _read("team_games", ["SEASON_YEAR", "TEAM_NAME", "GAME_DATE"])
    pg["pname"] = pg.PLAYER_NAME.map(norm)
    team_name = tg.groupby("tkey").TEAM_NAME.last()
    tdates = {k: g.date.sort_values().to_numpy() for k, g in tg.groupby(["season", "tkey"])}
    roster = {k: list(g.pname.unique()) for k, g in pg.groupby(["season", "tkey"])}
    league = set(zip(pg.season, pg.pname))

    def resolve(season, team, name):
        """Match a name to that team's NBA roster (exact, else close match); None if absent."""
        r = roster.get((season, team), [])
        if name in r:
            return name
        m = difflib.get_close_matches(name, r, 1, 0.75)
        return m[0] if m else None

    # --- salaries -> one row per player-team-season
    sal = pd.concat(pd.read_csv(f"{D}/salaries_{y}.csv") for y in SEASONS)
    sal["tkey"] = sal.team.str.split("-").str[-1]
    sal["sname"] = sal.player.map(norm)
    sal["pname"] = [resolve(s, t, n) for s, t, n in zip(sal.season, sal.tkey, sal.sname)]
    sal["matched"] = sal.pname.notna()
    sal["pname"] = sal.pname.fillna(sal.sname)
    sal = (sal.groupby(["season", "tkey", "pname"], as_index=False)
              .agg(player=("player", "first"), salary=("salary", "sum"), two_way=("two_way", "max"),
                   matched=("matched", "max")))

    # --- games played and window
    st = (pg.groupby(["season", "tkey", "pname"])
            .agg(played=("date", "size"), first=("date", "min"), last=("date", "max")).reset_index())
    nteams = pg.groupby(["season", "pname"]).tkey.nunique().rename("nteams").reset_index()
    df = sal.merge(st, how="left", on=["season", "tkey", "pname"]).merge(nteams, how="left", on=["season", "pname"])
    df["played"] = df.played.fillna(0).astype(int)
    df["team_games"] = [len(tdates[(s, t)]) for s, t in zip(df.season, df.tkey)]

    def missed(r):
        d = tdates[(r.season, r.tkey)]
        if r.played == 0:  # never played for this team: absent all season, or traded away
            return 0 if (r.season, r.pname) in league else len(d)
        if r.nteams == 1:
            return len(d) - r.played
        return max(((d >= r.first) & (d <= r.last)).sum() - r.played, 0)  # traded: only between first/last game

    df["missed"] = df.apply(missed, axis=1)

    # --- injured-list stints (Kaggle)
    il = pd.read_csv(f"{D}/injuries_kaggle.csv", parse_dates=["Date"])
    il = il[il.Date >= f"{min(SEASONS)}-07-01"].copy()
    il["season"] = il.Date.dt.year - (il.Date.dt.month < 7)
    il["tkey"] = il.Team.map(tkey)
    notes = il.Notes.str.lower()
    il["kind"] = None
    il.loc[il.Relinquished.notna() & notes.str.startswith("placed on il"), "kind"] = "placed"
    il.loc[il.Acquired.notna() & notes.str.contains("activated from il|returned"), "kind"] = "activated"
    il = il[il.kind.notna()]
    il["name"] = [resolve(s, t, norm(a if k == "activated" else r)) or norm(a if k == "activated" else r)
                  for s, t, k, a, r in zip(il.season, il.tkey, il.kind, il.Acquired, il.Relinquished)]
    rows = []
    for (season, name), g in il.sort_values("Date").groupby(["season", "name"]):
        ev = list(zip(g.Date, g.kind, g.tkey))
        for i, (d, k, t) in enumerate(ev):
            if k != "placed" or (season, t) not in tdates:
                continue
            dates = tdates[(season, t)]
            end = ev[i + 1][0] if i + 1 < len(ev) else dates[-1] + pd.Timedelta(days=1)  # next event ends the stint
            rows.append((season, t, name, int(((dates >= d.to_datetime64()) & (dates < end.to_datetime64())).sum())))
    ilm = (pd.DataFrame(rows, columns=["season", "tkey", "pname", "missed_il"])
             .groupby(["season", "tkey", "pname"], as_index=False).missed_il.sum())
    df = df.merge(ilm, how="left", on=["season", "tkey", "pname"])
    df["missed_il"] = df.missed_il.fillna(0).clip(upper=df.missed).astype(int)

    df["cost_missed"] = df.salary * df.missed / df.team_games
    df["cost_il"] = df.salary * df.missed_il / df.team_games
    df["team"] = df.tkey.map(team_name)
    df["season_label"] = df.season.map(lambda y: f"{y}-{str(y + 1)[2:]}")
    return df[["season", "season_label", "team", "player", "salary", "two_way", "matched", "team_games",
               "played", "missed", "missed_il", "cost_missed", "cost_il"]]


if __name__ == "__main__":
    df = build()
    assert (df.missed >= 0).all() and (df.played <= df.team_games).all() and (df.missed_il <= df.missed).all()
    print(df.groupby("season_label").agg(rows=("player", "size"), unmatched=("matched", lambda s: (~s).sum()),
                                          payroll_m=("salary", lambda s: round(s.sum() / 1e6)),
                                          cost_m=("cost_missed", lambda s: round(s.sum() / 1e6)),
                                          cost_il_m=("cost_il", lambda s: round(s.sum() / 1e6))))
    print(df[~df.matched].nlargest(8, "salary")[["season_label", "team", "player", "salary", "missed"]])
    print(df.nlargest(8, "cost_missed")[["season_label", "team", "player", "salary", "missed", "missed_il"]])
