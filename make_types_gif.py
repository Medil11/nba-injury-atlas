"""Animated GIF (720x900): the most common NBA injuries. Same look and toolkit as make_gif.py (it reuses its helpers).

Scene 1: top 10 injuries. Scene 2: what kind of injuries (waffle). Scene 3: common is not serious.
Run: python make_types_gif.py   (needs data/ like make_gif.py; ~30 s; no downloads)
"""
from PIL import Image, ImageDraw

import bodymap as bm
import injury_types as it
import make_gif as mg
from make_gif import BLUE, BOLD, DARKRED, GREY, INK, RED, REG, S, SLAB, GIFBuilder, ease, final, font, new_page

HOLD = 60
FOOT = "source: Pro Sports Transactions (via Kaggle) · left and right pooled"


def footer(d, line1, line2=FOOT):
    d.text((360 * S, 864 * S), line1, font=font(BOLD, 13), fill=GREY, anchor="ms")
    d.text((360 * S, 884 * S), line2, font=font(REG, 12), fill=GREY, anchor="ms")


def layer_of(img):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    return layer, ImageDraw.Draw(layer)


def shown(img, layer):
    return final(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"))


# ============================== scene 1: top 10 ==============================
def scene_top(d, t):
    sub = f"{len(d):,} injuries · {mg.fdate(d.placed.min(), False)} – {mg.fdate(d.placed.max(), False)} · injured-list placements"
    img, dr = new_page("The most common NBA injuries", sub)
    dr.text((690 * S, 138 * S), "days out on average", font=font(BOLD, 12), fill=GREY, anchor="rs")
    footer(dr, "injury = nature + body part · “knee injury” alone is not ranked (nature not stated)")
    X, BARW, ROW0, STEP, STAG, DUR = 30, 420, 152, 62, 6, 16
    first, ratio = t.iloc[0], t.injuries.iloc[0] / t.injuries.iloc[1]
    note_at = 4 + len(t) * STAG + DUR
    f_lab, f_num, f_avg = font(BOLD, 17), font(SLAB, 22), font(BOLD, 15)
    frames = []
    for f in range(note_at + 8 + HOLD):
        layer, ld = layer_of(img)
        for i, r in enumerate(t.itertuples()):
            p = ease((f - 4 - i * STAG) / DUR)
            if p <= 0:
                continue
            al, y, col = round(255 * p), ROW0 + i * STEP, DARKRED if i == 0 else BLUE
            w = BARW * r.injuries / first.injuries * p
            ld.text((X * S, (y + 16) * S), r.type, font=f_lab, fill=INK + (al,), anchor="ls")
            ld.rounded_rectangle([X * S, (y + 24) * S, (X + w) * S, (y + 46) * S], radius=4 * S, fill=col + (255,))
            ld.text(((X + w + 10) * S, (y + 35) * S), f"{round(r.injuries * p):,}", font=f_num, fill=col + (al,), anchor="lm")
            ld.text((690 * S, (y + 35) * S), f"{r.avg_days:.0f} days", font=f_avg, fill=(DARKRED if r.avg_days >= 30 else GREY) + (al,), anchor="rm")
        a = ease((f - note_at) / 8)
        if a > 0:
            al = round(255 * a)
            ld.text((360 * S, 790 * S), f"{first.type}: 1 injury in {round(100 / first.share)}, {ratio:.1f}× more than #2",
                    font=font(BOLD, 22), fill=DARKRED + (al,), anchor="mm")
            ld.text((360 * S, 820 * S), f"the top 10 make up {t.share.sum():.0f}% of all {len(d):,} injuries with a known body part",
                    font=font(BOLD, 15), fill=GREY + (al,), anchor="mm")
        frames.append(shown(img, layer))
    return frames


# ============================== scene 2: what kind of injuries (waffle) ==============================
OTHER = (150, 120, 90)
NAT_COL = {"Soreness / spasms": BLUE, "Sprain": DARKRED, "Strain": RED, "Bruise": (226, 163, 60), "Fracture": INK,
           "Tear": (128, 70, 160), "Concussion": (40, 150, 140), "Other natures": OTHER, it.UNSPECIFIED: (200, 197, 187)}


def natures(d):
    """Seven biggest stated natures, the rest as 'Other natures', then 'Not specified': (name, injuries, share, average days)."""
    n = it.by_nature(d)
    known = n[n.nature != it.UNSPECIFIED]
    row = lambda r: (r.nature, r.injuries, r.share, r.avg_days)
    rest = known.iloc[7:]
    other = ("Other natures", rest.injuries.sum(), rest.share.sum(), (rest.injuries * rest.avg_days).sum() / rest.injuries.sum())
    return [row(r) for r in known.head(7).itertuples()] + [other] + [row(r) for r in n[n.nature == it.UNSPECIFIED].itertuples()]


def scene_kind(d):
    cats = natures(d)
    soft = sum(c[1] for c in cats if c[0] in ("Soreness / spasms", "Sprain", "Strain", "Bruise"))
    stated = int((d.nature != it.UNSPECIFIED).sum())
    unspec = next(c[2] for c in cats if c[0] == it.UNSPECIFIED)
    img, dr = new_page("What kind of injuries?", f"{len(d):,} injuries · 1 square = 1% of injuries")
    footer(dr, "nature read from the injury note (“sprained ankle” → sprain)")
    cells = [int(c[2]) for c in cats]
    for i in sorted(range(len(cats)), key=lambda i: cats[i][2] - cells[i], reverse=True)[:100 - sum(cells)]:  # largest remainder
        cells[i] += 1
    squares = [NAT_COL[c[0]] for c, k in zip(cats, cells) for _ in range(k)]
    starts = [sum(cells[:i]) for i in range(len(cats))]
    X0, Y0, PITCH, SQ = 40, 170, 34, 30
    note_at = 4 + 100 // 3 + 6
    f_name, f_pct, f_sub = font(BOLD, 16), font(SLAB, 22), font(REG, 12)
    frames = []
    for f in range(note_at + 8 + HOLD):
        layer, ld = layer_of(img)
        k = min(100, max(0, 3 * (f - 4)))
        for i in range(k):
            x, y = X0 + (i % 10) * PITCH, Y0 + (i // 10) * PITCH
            ld.rounded_rectangle([x * S, y * S, (x + SQ) * S, (y + SQ) * S], radius=4 * S, fill=squares[i] + (255,))
        for j, c in enumerate(cats):
            a = ease((k - starts[j]) / 6)
            if a <= 0:
                continue
            al, y = round(255 * a), 172 + j * 46
            ld.rounded_rectangle([430 * S, (y + 2) * S, 448 * S, (y + 20) * S], radius=3 * S, fill=NAT_COL[c[0]] + (al,))
            ld.text((458 * S, (y + 11) * S), c[0], font=f_name, fill=INK + (al,), anchor="lm")
            ld.text((458 * S, (y + 30) * S), f"{c[1]:,.0f} injuries · {c[3]:.0f} days on average", font=f_sub, fill=GREY + (al,), anchor="lm")
            ld.text((690 * S, (y + 14) * S), f"{c[2]:.0f}%", font=f_pct, fill=INK + (al,), anchor="rm")
        a = ease((f - note_at) / 8)
        if a > 0:
            al = round(255 * a)
            ld.text((360 * S, 700 * S), f"Soreness, sprains, strains, bruises: {100 * soft / stated:.0f}% of stated injuries",
                    font=font(BOLD, 21), fill=DARKRED + (al,), anchor="mm")
            ld.text((360 * S, 732 * S), f"{unspec:.0f}% of injuries (“knee injury”, “hamstring injury”…) do not say what happened",
                    font=font(BOLD, 15), fill=GREY + (al,), anchor="mm")
        frames.append(shown(img, layer))
    return frames


# ============================== scene 3: common is not serious ==============================
def scene_serious(d):
    t = it.by_type(d, 999)
    common = t.iloc[0]
    serious = t[t.injuries >= 100].sort_values("avg_days").iloc[-1]  # longest average absence among frequent injuries
    assert serious.type != common.type
    img, dr = new_page("Common is not serious", "most frequent injury vs longest absences among injuries seen 100+ times")
    footer(dr, "absence = days from the injured-list placement to the first game back", FOOT)
    cards = [(40, "Most common", common, BLUE), (370, "Longest absences", serious, DARKRED)]
    for x, head, r, col in cards:
        dr.rounded_rectangle([x * S, 140 * S, (x + 310) * S, 530 * S], radius=14 * S, fill=mg.CREAM)
        dr.text(((x + 155) * S, 172 * S), head, font=font(BOLD, 14), fill=GREY, anchor="mm")
        dr.text(((x + 155) * S, 214 * S), r.type, font=font(SLAB, 28), fill=col, anchor="mm")
        dr.text(((x + 155) * S, 350 * S), "injuries", font=font(BOLD, 16), fill=GREY, anchor="mm")
        dr.text(((x + 155) * S, 485 * S), "days out on average", font=font(BOLD, 16), fill=GREY, anchor="mm")
    top_days = max(common.days, serious.days)
    fewer, longer, share = common.injuries / serious.injuries, serious.avg_days / common.avg_days, 100 * serious.days / common.days
    frames = []
    for f in range(100 + HOLD):
        layer, ld = layer_of(img)
        p = ease((f - 4) / 26)
        for x, _, r, col in cards:
            ld.text(((x + 155) * S, 300 * S), f"{round(r.injuries * p):,}", font=font(SLAB, 64), fill=col + (255,), anchor="mm")
            ld.text(((x + 155) * S, 435 * S), f"{r.avg_days * p:.0f}", font=font(SLAB, 64), fill=col + (255,), anchor="mm")
        b = ease((f - 36) / 20)
        if b > 0:
            ld.text((360 * S, 572 * S), "days missed in total", font=font(BOLD, 14), fill=GREY + (round(255 * b),), anchor="mm")
            for i, (_, _, r, col) in enumerate(cards):
                y, w = 600 + i * 50, 400 * r.days / top_days * b
                ld.text((30 * S, (y + 15) * S), r.type, font=font(BOLD, 15), fill=INK + (round(255 * b),), anchor="lm")
                ld.rounded_rectangle([200 * S, y * S, (200 + w) * S, (y + 30) * S], radius=4 * S, fill=col + (255,))
                ld.text(((200 + w + 10) * S, (y + 15) * S), f"{round(r.days * b):,}", font=font(SLAB, 20), fill=col + (round(255 * b),), anchor="lm")
        a = ease((f - 62) / 8)
        if a > 0:
            al = round(255 * a)
            ld.text((360 * S, 760 * S), f"{fewer:.0f}× fewer injuries, {longer:.0f}× longer absences", font=font(BOLD, 22), fill=DARKRED + (al,), anchor="mm")
            ld.text((360 * S, 792 * S), f"{serious.type.lower()}s still cost {share:.0f}% as many days as {common.type.lower()}s", font=font(BOLD, 15), fill=GREY + (al,), anchor="mm")
        frames.append(shown(img, layer))
    return frames


def main(out="injury_types.gif"):
    d = it.classify(bm.injuries(it.SEASONS))
    t = it.by_type(d)
    print(t.round(1).to_string())
    a, b, c = scene_top(d, t), scene_kind(d), scene_serious(d)
    fade = lambda x, y, n: [Image.blend(x, y, (i + 1) / (n + 1)) for i in range(n)]
    frames = a + fade(a[-1], b[0], 8) + b + fade(b[-1], c[0], 8) + c + fade(c[-1], a[0], 8)  # loops back to the empty chart
    builder = GIFBuilder(mg.W, mg.H, mg.FPS)
    builder.add_frames(frames)
    return builder.save(out, num_colors=128)


if __name__ == "__main__":
    main()
