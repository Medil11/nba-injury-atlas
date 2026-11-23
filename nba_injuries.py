import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import altair as alt
    from prep import build

    df = build()
    return alt, build, df, mo


@app.cell
def _(df, mo):
    seasons = mo.ui.multiselect(list(df.season_label.unique()), value=list(df.season_label.unique()), label="Seasons")
    metric = mo.ui.dropdown(
        {"All games missed": "cost_missed", "On the injured list": "cost_il"},
        value="All games missed", label="Cost",
    )
    mo.hstack([seasons, metric], justify="start")
    return metric, seasons


@app.cell
def _(df, metric, mo, seasons):
    d = df[df.season_label.isin(seasons.value)]
    col = metric.value
    mo.stop(d.empty, mo.md("Select at least one season."))
    total = d[col].sum()
    top = d.loc[d[col].idxmax()]
    mo.hstack([
        mo.stat(f"${total / 1e6:,.0f}M", label="Total cost", caption=f"{len(seasons.value)} season(s)"),
        mo.stat(f"${d.groupby('team')[col].sum().mean() / 1e6:,.1f}M", label="Average per franchise"),
        mo.stat(f"${top[col] / 1e6:,.1f}M", label="Largest single cost", caption=f"{top.player} ({top.season_label})"),
    ], justify="start")
    return col, d


@app.cell
def _(alt, col, d, mo):
    by_team = d.groupby("team", as_index=False)[col].sum().sort_values(col, ascending=False)
    by_team["cout_M"] = (by_team[col] / 1e6).round(1)
    chart = (
        alt.Chart(by_team, title="Cost of absences by franchise ($M)")
        .mark_bar()
        .encode(
            x=alt.X("cout_M:Q", title=None),
            y=alt.Y("team:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("team:N", title="Team"), alt.Tooltip("cout_M:Q", title="$M")],
        )
        .properties(height=alt.Step(18), width=520)
    )
    mo.ui.altair_chart(chart)
    return


@app.cell
def _(alt, col, d, df, mo):
    by_season = df.groupby("season_label", as_index=False)[col].sum()
    by_season["cout_M"] = (by_season[col] / 1e6).round(1)
    trend = (
        alt.Chart(by_season, title="Total cost per season, whole league ($M)")
        .mark_bar()
        .encode(
            x=alt.X("season_label:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("cout_M:Q", title=None),
            tooltip=[alt.Tooltip("season_label:N", title="Season"), alt.Tooltip("cout_M:Q", title="$M")],
        )
        .properties(width=420, height=220)
    )
    mo.ui.altair_chart(trend)
    return


@app.cell
def _(col, d, mo):
    players = (
        d.nlargest(25, col)[["season_label", "team", "player", "salary", "team_games", "missed", "missed_il", col]]
        .rename(columns={"season_label": "season", "team": "team", "player": "player", "salary": "salary",
                         "team_games": "team games", "missed": "missed", "missed_il": "of which on injured list", col: "cost"})
    )
    mo.vstack([mo.md("### 25 largest individual costs"),
               mo.ui.table(players.round(0).reset_index(drop=True), selection=None, format_mapping={"salary": "${:,.0f}".format, "cost": "${:,.0f}".format})])
    return


@app.cell
def _(mo):
    mo.md(
        """
        **Definitions and limits**
        - *Cost of a missed game* = salary ÷ team games. *Missed* = team games (regular season) minus games played: injury, rest and suspension all count the same.
        - *Injured list* = stints on the injured list according to the Kaggle dataset (Pro Sports Transactions), which ends in April 2023. Hence seasons 2018-19 to 2022-23.
        - Player traded mid-season: only games between his first and last game with the team are counted (possible underestimate).
        - HoopsHype and NBA player names are matched approximately within the team; a player absent all season counts every game as missed.
        """
    )
    return


if __name__ == "__main__":
    app.run()
