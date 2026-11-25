"""What kind of injuries are the most common? Injury notes ("sprained left ankle") -> nature (sprain) + body part (ankle).

Reuses bodymap: same injured-list placements, same body-part rules, same absence days. A "type" is nature + body part
("Ankle sprain"); notes with no stated nature ("knee injury") are counted as "Not specified" and left out of the ranking.
"""
import re

import bodymap as bm

SEASONS = range(2010, 2023)  # 2010-11 to 2022-23: more placements than bodymap's default, so the ranking is steadier

# first matching rule wins
NATURES = [
    ("Concussion", r"concussion"),
    ("Fracture", r"fractur|broken|\bbreak\b|stress reaction"),
    ("Tear", r"\btorn\b|\btear\b|tearing|rupture"),
    ("Dislocation", r"dislocat|subluxat|separated"),
    ("Sprain", r"sprain|hyperextend|\bturned\b|\brolled\b"),
    ("Strain", r"strain|pulled"),
    ("Bruise", r"bruis|contusion|\bhematoma"),
    ("Inflammation", r"inflam|tendin|bursitis|swell|irritat|\bfasciitis|\bsyndrome"),
    ("Soreness / spasms", r"sore|tight|stiff|spasm|cramp|\bpain|discomfort|fatigue|spasms|\bache"),
    ("Surgery", r"surger|surgical|arthroscop|post-?op"),
]
UNSPECIFIED = "Not specified"
SHORT = {  # body-part wording inside an injury name ("Ankle sprain")
    "head": "Head", "neck": "Neck", "shoulder": "Shoulder", "chest": "Rib", "abdomen": "Abdominal", "upper_back": "Upper back",
    "lower_back": "Lower back", "hip": "Hip / groin", "arm": "Elbow / arm", "hand": "Hand / wrist", "quad": "Thigh", "hamstring": "Hamstring",
    "knee": "Knee", "shin": "Lower leg", "calf": "Calf", "achilles": "Achilles", "ankle": "Ankle", "foot": "Foot / toe",
}
NOUN = {"Soreness / spasms": "soreness"}


def nature(note):
    detail = re.sub(r"^placed on il\s*", "", str(note).lower())
    return next((n for n, pat in NATURES if re.search(pat, detail)), UNSPECIFIED)


def classify(inj):
    """Injuries with a known body part, plus `nature` and `type` ("Ankle sprain"; "Concussion" has no body part)."""
    d = inj[inj.region.isin(bm.LABEL)].copy()
    d["nature"] = d.note.map(nature)
    d["type"] = [n if n in ("Concussion", UNSPECIFIED) else f"{SHORT[r]} {NOUN.get(n, n.lower())}" for r, n in zip(d.region, d.nature)]
    return d


def by_type(d, top=10, by="injuries", min_n=1):
    """Injuries (nature stated), ranked by `by` ('injuries', 'days' or 'avg_days'): count, share of all located injuries,
    cumulated and average days missed. `min_n` hides rare types (their average is noise)."""
    t = d[d.nature != UNSPECIFIED].groupby(["type", "nature"]).days.agg(injuries="size", days="sum", avg_days="mean").reset_index()
    t["share"] = 100 * t.injuries / len(d)
    return t[t.injuries >= min_n].sort_values(by, ascending=False).head(top).reset_index(drop=True)


def by_nature(d):
    """What kind of injury, whatever the body part: count, share, average days missed."""
    t = d.groupby("nature").days.agg(injuries="size", avg_days="mean").sort_values("injuries", ascending=False)
    t["share"] = 100 * t.injuries / len(d)
    return t.reset_index()


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.width", 200)
    d = classify(bm.injuries(SEASONS))
    print(len(d), "located injuries |", (d.nature != UNSPECIFIED).sum(), "with a stated nature")
    print(by_type(d, 25).round(1).to_string())
    print(by_nature(d).round(1).to_string())
    print(d[d.nature == "Surgery"].note.value_counts().head(8).to_string())
    assert abs(by_nature(d).share.sum() - 100) < 1e-6
