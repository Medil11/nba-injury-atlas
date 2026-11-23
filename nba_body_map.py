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
    seasons = mo.ui.multiselect(labels, value=labels, label="Seasons")
    metric = mo.ui.dropdown({"Cumulative days missed": "days", "Number of injuries": "injuries"},
                            value="Cumulative days missed", label="Color")
    mo.hstack([seasons, metric], justify="start")
    return metric, seasons


@app.cell
def _(bodymap, inj, metric, mo, seasons):
    years = [int(s[:4]) for s in seasons.value]
    sel = inj[inj.season.isin(years)]
    mo.stop(sel.empty, mo.md("Select at least one season."))
    tab = bodymap.by_region(sel)
    mo.vstack([
        mo.Html(bodymap.poster(sel, metric.value)),
        mo.md("### Detail by body part"),
        mo.ui.table(tab.rename(columns={"label": "body part", "injuries": "injuries", "days": "total days", "avg_days": "avg days"})
                      [["body part", "injuries", "total days", "avg days"]], selection=None),
        mo.md("Left and right are pooled. Injured-list placements with no detail (just “placed on IL”), illnesses and COVID protocols are not located. "
              "An absence runs from the placement on the injured list to the player's return (first game played) or his next transaction (mid-April otherwise)."),
    ])
    return


if __name__ == "__main__":
    app.run()
