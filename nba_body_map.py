import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import bodymap

    inj = bodymap.injuries()
    labels = [f"{y}-{str(y + 1)[2:]}" for y in bodymap.SEASONS]
    return bodymap, inj, labels, mo


@app.cell
def _(labels, mo):
    seasons = mo.ui.multiselect(labels, value=labels, label="Saisons")
    metric = mo.ui.dropdown({"Jours d'absence cumulés": "days", "Nombre de blessures": "injuries"},
                            value="Jours d'absence cumulés", label="Couleur")
    mo.hstack([seasons, metric], justify="start")
    return metric, seasons


@app.cell
def _(bodymap, inj, metric, mo, seasons):
    years = [int(s[:4]) for s in seasons.value]
    sel = inj[inj.season.isin(years)]
    mo.stop(sel.empty, mo.md("Sélectionne au moins une saison."))
    tab = bodymap.by_region(sel)
    mo.vstack([
        mo.Html(bodymap.poster(sel, metric.value)),
        mo.md("### Détail par partie du corps"),
        mo.ui.table(tab.rename(columns={"label": "partie", "injuries": "blessures", "days": "jours cumulés", "avg_days": "jours moyens"})
                      [["partie", "blessures", "jours cumulés", "jours moyens"]], selection=None),
        mo.md("Gauche et droite sont regroupées. Les mises sur la liste des blessés sans détail (« placed on IL » seul), les maladies et les protocoles COVID ne sont pas localisés. "
              "Une absence = de la mise sur la liste des blessés au retour du joueur (premier match joué) ou à sa transaction suivante (mi-avril sinon)."),
    ])
    return


if __name__ == "__main__":
    app.run()
