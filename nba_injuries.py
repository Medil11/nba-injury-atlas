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
    seasons = mo.ui.multiselect(list(df.season_label.unique()), value=list(df.season_label.unique()), label="Saisons")
    metric = mo.ui.dropdown(
        {"Tous matchs manqués": "cost_missed", "Sur la liste des blessés": "cost_il"},
        value="Tous matchs manqués", label="Coût",
    )
    mo.hstack([seasons, metric], justify="start")
    return metric, seasons


@app.cell
def _(df, metric, mo, seasons):
    d = df[df.season_label.isin(seasons.value)]
    col = metric.value
    mo.stop(d.empty, mo.md("Sélectionne au moins une saison."))
    total = d[col].sum()
    top = d.loc[d[col].idxmax()]
    mo.hstack([
        mo.stat(f"${total / 1e6:,.0f} M", label="Coût total", caption=f"{len(seasons.value)} saison(s)"),
        mo.stat(f"${d.groupby('team')[col].sum().mean() / 1e6:,.1f} M", label="Moyenne par franchise"),
        mo.stat(f"${top[col] / 1e6:,.1f} M", label="Plus gros coût individuel", caption=f"{top.player} ({top.season_label})"),
    ], justify="start")
    return col, d


@app.cell
def _(alt, col, d, mo):
    by_team = d.groupby("team", as_index=False)[col].sum().sort_values(col, ascending=False)
    by_team["cout_M"] = (by_team[col] / 1e6).round(1)
    chart = (
        alt.Chart(by_team, title="Coût des absences par franchise (M$)")
        .mark_bar()
        .encode(
            x=alt.X("cout_M:Q", title=None),
            y=alt.Y("team:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("team:N", title="Équipe"), alt.Tooltip("cout_M:Q", title="M$")],
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
        alt.Chart(by_season, title="Coût total par saison, ligue entière (M$)")
        .mark_bar()
        .encode(
            x=alt.X("season_label:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("cout_M:Q", title=None),
            tooltip=[alt.Tooltip("season_label:N", title="Saison"), alt.Tooltip("cout_M:Q", title="M$")],
        )
        .properties(width=420, height=220)
    )
    mo.ui.altair_chart(trend)
    return


@app.cell
def _(col, d, mo):
    players = (
        d.nlargest(25, col)[["season_label", "team", "player", "salary", "team_games", "missed", "missed_il", col]]
        .rename(columns={"season_label": "saison", "team": "équipe", "player": "joueur", "salary": "salaire",
                         "team_games": "matchs équipe", "missed": "manqués", "missed_il": "dont liste des blessés", col: "coût"})
    )
    mo.vstack([mo.md("### 25 plus gros coûts individuels"),
               mo.ui.table(players.round(0).reset_index(drop=True), selection=None, format_mapping={"salaire": "${:,.0f}".format, "coût": "${:,.0f}".format})])
    return


@app.cell
def _(mo):
    mo.md(
        """
        **Définitions et limites**
        - *Coût d'un match manqué* = salaire ÷ matchs de l'équipe. *Manqué* = matchs de l'équipe (saison régulière) moins matchs joués : blessure, repos et suspension comptent pareil.
        - *Liste des blessés* = séjours sur la liste des blessés d'après le dataset Kaggle (Pro Sports Transactions), qui s'arrête en avril 2023. D'où les saisons 2018-19 à 2022-23.
        - Joueur échangé en cours de saison : seuls les matchs entre son premier et son dernier match avec l'équipe sont comptés (sous-estimation possible).
        - Les noms de HoopsHype et de la NBA sont rapprochés par nom approché au sein de l'équipe ; un joueur absent toute la saison compte tous les matchs manqués.
        """
    )
    return


if __name__ == "__main__":
    app.run()
