import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import altair as alt
    import bodymap
    import injury_types as it

    d = it.classify(bodymap.injuries(it.SEASONS))
    labels = [f"{y}-{str(y + 1)[2:]}" for y in it.SEASONS]
    return alt, d, it, labels, mo


@app.cell
def _(labels, mo):
    seasons = mo.ui.multiselect(labels, value=labels, label="Seasons")
    metric = mo.ui.dropdown({"Number of injuries": "injuries", "Cumulative days missed": "days", "Average days missed": "avg_days"},
                            value="Number of injuries", label="Rank by")
    min_n = mo.ui.slider(1, 100, value=20, label="Minimum injuries per type")
    mo.hstack([seasons, metric, min_n], justify="start")
    return metric, min_n, seasons


@app.cell
def _(alt, d, it, metric, min_n, mo, seasons):
    sel = d[d.season.isin([int(s[:4]) for s in seasons.value])]
    mo.stop(sel.empty, mo.md("Select at least one season."))
    t = it.by_type(sel, top=15, by=metric.value, min_n=min_n.value)
    mo.stop(t.empty, mo.md("No injury type has that many cases: lower the minimum."))
    chart = (
        alt.Chart(t, title=f"Top injuries by {metric.selected_key.lower()}")
        .mark_bar()
        .encode(
            x=alt.X(f"{metric.value}:Q", title=None),
            y=alt.Y("type:N", sort="-x", title=None),
            color=alt.Color("nature:N", title="Nature"),
            tooltip=[alt.Tooltip("type:N", title="Injury"), alt.Tooltip("injuries:Q", title="Injuries"), alt.Tooltip("days:Q", title="Days missed"),
                     alt.Tooltip("avg_days:Q", title="Average days", format=".1f"), alt.Tooltip("share:Q", title="% of injuries", format=".1f")],
        )
        .properties(height=alt.Step(20), width=520)
    )
    mo.vstack([
        mo.hstack([
            mo.stat(f"{len(sel):,}", label="Injuries with a known body part"),
            mo.stat(f"{100 * (sel.nature != it.UNSPECIFIED).mean():.0f}%", label="State their nature", caption="“knee injury” alone does not"),
        ], justify="start"),
        mo.ui.altair_chart(chart),
        mo.md("### By nature"),
        mo.ui.table(it.by_nature(sel).round(1).rename(columns={"avg_days": "avg days", "share": "% of injuries"}), selection=None),
        mo.md("The nature is read from the injury note (“sprained ankle” → sprain); left and right are pooled. Injured-list placements with no detail, "
              "illnesses and COVID protocols are not located. An absence runs from the placement on the injured list to the first game played."),
    ])
    return


if __name__ == "__main__":
    app.run()
