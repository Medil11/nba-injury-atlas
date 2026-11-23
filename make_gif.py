"""Animated GIF (720x900) of NBA injuries, built with the slack-gif-creator toolkit.

Scene 1: body heat map. Scene 2: ACL tears, injury -> first game back (with player photos). Scene 3: what the knee costs.
Run: python make_gif.py   (needs data/ from the notebooks; ~2 min; downloads headshots once into data/headshots/)
"""
import glob
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path.home() / ".claude/skills/slack-gif-creator"))
from core.easing import interpolate  # noqa: E402
from core.gif_builder import GIFBuilder  # noqa: E402

import bodymap as bm  # noqa: E402
import prep  # noqa: E402

W, H, S, FPS = 720, 900, 2, 20  # S = supersampling for smooth edges
INK, GREY, LINE = (27, 27, 26), (107, 107, 102), (59, 59, 56)
BG, CREAM = (232, 229, 218), (240, 236, 225)
BLUE, RED, DARKRED = (70, 98, 214), (212, 84, 90), (168, 35, 43)
END = pd.Timestamp("2023-04-16")  # last date of the Kaggle injury data
FONTS = Path("C:/Windows/Fonts")


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), round(size * S))


SLAB, BOLD, REG = "ROCKEB.TTF", "arialbd.ttf", "arial.ttf"


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def f1(x):  # one decimal: 9.6
    return f"{x:,.1f}"


def fm(x):  # millions of dollars, no decimals: 753
    return f"{round(x / 1e6):,}"


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fdate(t, day=True):
    return f"{MONTHS[t.month - 1]} {t.day}, {t.year}" if day else f"{MONTHS[t.month - 1]} {t.year}"


def new_page(title, sub):
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)
    d.text((360 * S, 20 * S), "github.com/Medil11", font=font(BOLD, 12), fill=GREY, anchor="mm")  # credit, on every slide
    d.text((360 * S, 62 * S), title, font=font(SLAB, 33), fill=INK, anchor="ms")
    d.text((360 * S, 94 * S), sub, font=font(BOLD, 17), fill=GREY, anchor="ms")
    return img, d


def final(img):
    return img.resize((W, H), Image.Resampling.LANCZOS)


def ease(p):
    return interpolate(0, 1, min(max(p, 0), 1), "ease_out")


# ============================== scene 1: body heat map ==============================
SC, OY, FRONT_OX, BACK_OX = 1.45, 132, 117, 343  # figure scale, top, and left of each figure (room left and right for the call-outs)


def px(ox, x, y):  # figure coordinates (200 x 415 box) -> supersampled pixels
    return (ox + SC * x) * S, (OY + SC * y) * S


def draw_items(d, ox, items):
    for s in items:
        if s[0] == "e":
            d.ellipse([*px(ox, s[1] - s[3], s[2] - s[4]), *px(ox, s[1] + s[3], s[2] + s[4])], fill=255)
        else:
            d.rounded_rectangle([*px(ox, s[1], s[2]), *px(ox, s[1] + s[3], s[2] + s[4])], radius=s[5] * SC * S, fill=255)


def spline(pts, closed=True, n=8):
    """Catmull-Rom curve through pts (figure coordinates)."""
    p = list(pts) if closed else [pts[0], *pts, pts[-1]]
    out = []
    for i in range(len(p) if closed else len(p) - 3):
        p0, p1, p2, p3 = (p[(i + k - 1) % len(p)] for k in range(4)) if closed else p[i:i + 4]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * (2 * p1[j] + (p2[j] - p0[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (3 * p1[j] - p0[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    return out if closed else out + [pts[-1]]


mirror = lambda pts: [(200 - x, y) for x, y in pts]
# human outline, left half of a 200 x 415 box (x < 100); right side is mirrored
TORSO_L = [(92, 50), (91, 62), (78, 67), (62, 72), (55, 82), (60, 96), (68, 110), (72, 126), (73, 142), (68, 160), (66, 176), (68, 190), (84, 203), (100, 207)]
ARM_L = [(52, 76), (44, 90), (40, 112), (37, 140), (35, 166), (33, 190), (32, 206), (31, 222), (32, 236), (37, 242), (43, 238), (48, 228),
         (49, 214), (50, 206), (52, 190), (54, 170), (56, 148), (59, 124), (61, 104), (63, 90), (62, 78)]
LEG_L = [(66, 176), (63, 205), (64, 235), (68, 262), (72, 285), (72, 302), (70, 322), (72, 345), (75, 366), (75, 382), (70, 396), (66, 404),
         (70, 410), (82, 411), (90, 408), (91, 398), (88, 384), (87, 366), (88, 346), (92, 324), (96, 300), (98, 282), (99, 258), (99, 230),
         (100, 205), (92, 190)]
BODY_POLYS = [TORSO_L + mirror(TORSO_L[::-1]), ARM_L, mirror(ARM_L), LEG_L, mirror(LEG_L)]
# thin anatomical lines (left side; mirrored automatically)
LINES_COMMON = [[(93, 65), (84, 66), (72, 70), (63, 74)]]
LINES_FRONT = [[(75, 92), (82, 101), (92, 103), (99, 99)], [(100, 68), (100, 100)], [(100, 106), (100, 152)], [(92, 118), (100, 118)],
               [(91, 130), (100, 130)], [(92, 142), (100, 142)], [(76, 164), (88, 180), (100, 190)], [(77, 286), (84, 282), (91, 286)]]
LINES_BACK = [[(78, 82), (90, 90), (90, 104), (82, 110)], [(94, 62), (84, 70), (70, 76)], [(70, 190), (84, 196), (99, 194)], [(78, 290), (90, 290)]]
LINES_CENTER = [[(100, 207), (100, 286)]]
LINES_CENTER_BACK = [[(100, 58), (100, 206)]]


def body_masks():
    """Human silhouette + outline ring + anatomical lines + one soft heat mask per body part (both figures)."""
    size = (W * S, H * S)
    sil, lines = Image.new("L", size, 0), Image.new("L", size, 0)
    d, dl = ImageDraw.Draw(sil), ImageDraw.Draw(lines)
    for ox, shapes, extra, center in ((FRONT_OX, bm.FRONT, LINES_FRONT, LINES_CENTER), (BACK_OX, bm.BACK, LINES_BACK, LINES_CENTER_BACK)):
        for poly in BODY_POLYS:
            d.polygon([px(ox, *p) for p in spline(poly)], fill=255)
        d.ellipse([*px(ox, 83.5, 8), *px(ox, 116.5, 54)], fill=255)  # head
        for ln in LINES_COMMON + extra:
            for side in (ln, mirror(ln)):
                dl.line([px(ox, *p) for p in spline(side, closed=False)], fill=255, width=round(1.4 * S), joint="curve")
        for ln in center:
            dl.line([px(ox, *p) for p in ln], fill=255, width=round(1.4 * S))
    sil = sil.filter(ImageFilter.GaussianBlur(S)).point(lambda v: 255 if v > 127 else 0)
    ring = ImageChops.subtract(sil.filter(ImageFilter.MaxFilter(7)), sil.filter(ImageFilter.MinFilter(7)))
    lines = ImageChops.multiply(lines.filter(ImageFilter.GaussianBlur(0.6 * S)), sil).point(lambda v: int(v * 0.55))
    masks = {}
    for reg in bm.LABEL:
        m = Image.new("L", size, 0)
        dm = ImageDraw.Draw(m)
        for ox, shapes in ((FRONT_OX, bm.FRONT), (BACK_OX, bm.BACK)):
            if reg in shapes:
                draw_items(dm, ox, shapes[reg])
        m = m.filter(ImageFilter.GaussianBlur(5 * S)).point(lambda v: min(255, int(v * 1.7)))
        masks[reg] = ImageChops.multiply(m, sil)
    return sil, ring, lines, masks


# zones with a call-out: front figure -> left column, back figure -> right column (each list sorted top to bottom)
LEFT = ["shoulder", "arm", "hip", "hand", "quad", "knee", "shin", "ankle", "foot"]
RIGHT = ["head", "lower_back", "hamstring", "calf", "achilles"]
ANCHOR = {"shoulder": (66, 76), "arm": (50, 116), "hip": (84, 171), "hand": (40, 222), "quad": (84, 232), "knee": (84, 290),
          "shin": (82, 332), "ankle": (80, 376), "foot": (78, 398),
          "head": (100, 28), "lower_back": (116, 135), "hamstring": (116, 232), "calf": (118, 332), "achilles": (120, 365)}


def spread(ys, gap=60, lo=150, hi=755):
    """Call-out heights: as close as possible to their zone, at least `gap` apart."""
    out = []
    for y in ys:
        out.append(max(y, lo) if not out else max(y, out[-1] + gap))
    shift = max(out[-1] - hi, 0)
    return [y - shift for y in out]


def scene_body(inj, tab, g):
    vals = dict(zip(tab.region, tab.days))
    count = dict(zip(tab.region, tab.injuries))
    vmax, costliest = max(vals.values()), max(vals, key=vals.get)
    located, placed = int(tab.injuries.sum()), len(inj)
    sub = f"{located:,} injuries · {fdate(inj.placed.min(), False)} – {fdate(inj.placed.max(), False)} · color = cumulative days missed"
    img, d = new_page("Where do NBA players get hurt?", sub)
    for i in range(10):
        d.rectangle([(250 + i * 22) * S, 826 * S, (272 + i * 22) * S, 838 * S], fill=hex_rgb(bm._color(i, 9)))
    d.text((240 * S, 837 * S), "less", font=font(REG, 12), fill=GREY, anchor="rs")
    d.text((480 * S, 837 * S), "more days missed", font=font(REG, 12), fill=GREY, anchor="ls")
    d.text((360 * S, 864 * S), f"{located:,} of {placed:,} injured-list placements have a known body part",
           font=font(BOLD, 13), fill=GREY, anchor="ms")
    d.text((360 * S, 884 * S), "number = injuries · example = longest absence · photos: nba.com · source: Pro Sports Transactions (Kaggle)",
           font=font(REG, 12), fill=GREY, anchor="ms")
    sil, ring, lines, masks = body_masks()
    img.paste(CREAM, mask=sil)

    ids = g.groupby("n").PLAYER_ID.last()
    ex = inj[inj.region.isin(LEFT + RIGHT)].sort_values("days").groupby("region").tail(1).set_index("region")  # longest absence per zone
    cards = {}
    for left, regs in ((True, LEFT), (False, RIGHT)):
        for reg, y in zip(regs, spread([OY + SC * ANCHOR[r][1] for r in regs])):
            r = ex.loc[reg]
            cards[reg] = dict(left=left, y=y, n=int(count[reg]), label=bm.LABEL[reg], who=f"{short(r.player)}, {r.team}",
                              photo=headshot(player_id(r.player, ids), 44))
    f_num, f_lab, f_who = font(BOLD, 22), font(BOLD, 11), font(REG, 10)

    order = sorted(vals, key=vals.get)  # least injured first, the knee lands last
    start = {r: 4 + 2 * i for i, r in enumerate(order)}
    DUR, HOLD = 14, 60
    frames = []
    for f in range(4 + 2 * len(order) + DUR + HOLD):
        im = img.copy()
        for reg in order:
            p = ease((f - start[reg]) / DUR)
            if p > 0:
                im.paste(tuple(round(c0 + (c1 - c0) * p) for c0, c1 in zip(CREAM, hex_rgb(bm._color(vals[reg], vmax)))), mask=masks[reg])
        im.paste(LINE, mask=lines)
        im.paste(LINE, mask=ring)
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for reg, c in cards.items():
            a, p = ease((f - start[reg] - 2) / 10), ease((f - start[reg]) / 16)
            if a <= 0:
                continue
            al, left = round(255 * a), c["left"]
            col = (DARKRED if reg == costliest else INK) + (al,)
            tx = 58 if left else 662
            anchor = "l" if left else "r"
            ld.text((tx * S, (c["y"] - 10) * S), str(c["n"]), font=f_num, fill=col, anchor=anchor + "m")
            ld.text((tx * S, (c["y"] + 7) * S), c["label"], font=f_lab, fill=col, anchor=anchor + "m")
            ld.text((tx * S, (c["y"] + 20) * S), c["who"], font=f_who, fill=GREY + (al,), anchor=anchor + "m")
            width = max(ld.textlength(c["who"], font=f_who), ld.textlength(c["label"], font=f_lab)) / S
            t = c["photo"].copy()
            t.putalpha(t.getchannel("A").point(lambda v: round(v * a)))
            layer.alpha_composite(t, (round((5 if left else 671) * S), round((c["y"] - 22) * S)))
            sx, sy = (tx + width + 6 if left else tx - width - 6) * S, c["y"] * S
            ex_, ey_ = px(FRONT_OX if left else BACK_OX, *ANCHOR[reg])
            ld.line([sx, sy, sx + (ex_ - sx) * p, sy + (ey_ - sy) * p], fill=(80, 80, 76, round(200 * a)), width=S)
            if p > 0.97:
                ld.ellipse([ex_ - 4 * S, ey_ - 4 * S, ex_ + 4 * S, ey_ + 4 * S], fill=(255, 255, 255, al), outline=LINE + (al,), width=S)
        frames.append(final(Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")))
    return frames


# ============================== scene 2: ACL tears ==============================
ACL = r"\bacl\b|cruciate"


def aliases(name):
    """'Nicolas Claxton / Nic Claxton', 'John Wall (Hildred)' -> ['Nicolas Claxton', 'Nic Claxton'], ['John Wall']."""
    return [a.strip() for a in re.sub(r"\s*\(.*?\)", "", name).split(" / ")]


def short(name):
    name = aliases(name)[-1]  # most recent name
    p = name.split()
    return f"{p[0][0]}. {' '.join(p[1:])}" if len(p) > 1 and "." not in p[0] else name


def player_id(name, ids):
    return next((ids[prep.norm(a)] for a in aliases(name) if prep.norm(a) in ids.index), None)


def games():
    g = pd.concat(pd.read_csv(f, usecols=["PLAYER_ID", "PLAYER_NAME", "GAME_DATE"]) for f in glob.glob("data/player_games_*.csv"))
    g = g.dropna(subset=["PLAYER_ID"]).astype({"PLAYER_ID": int})
    g["n"] = g.PLAYER_NAME.map(prep.norm)
    g["d"] = pd.to_datetime(g.GAME_DATE)
    return g.sort_values("d")  # sorted, so .last() gives a name's latest id (old logs carry a wrong id for some players, e.g. Rubio)


def tears(inj, g):
    """Distinct ACL tears: (player, placed on the injured list, first game played afterwards or None, NBA player id).

    The dataset's 'activated' records are incomplete or wrong, so the return is the first game in the game logs."""
    dates = {n: x.d.sort_values().to_numpy() for n, x in g.groupby("n")}
    ids = g.groupby("n").PLAYER_ID.last()
    out = {}
    for r in inj[inj.note.str.contains(ACL)].sort_values("placed").itertuples():
        n = prep.norm(r.player)
        arr = dates.get(n, np.array([], dtype="datetime64[ns]"))
        i = arr.searchsorted(r.placed.to_datetime64(), side="right")
        back = pd.Timestamp(arr[i]) if i < len(arr) and pd.Timestamp(arr[i]) <= END else None
        out.setdefault((n, back), (r.player, r.placed, back, ids.get(n)))  # same return = same tear (re-placed each season): keep the first
    return sorted(out.values(), key=lambda t: t[1])


def make_cost():
    """Salary paid during a stint: season salary pro-rated over the regular-season days spent on the injured list."""
    sal = prep.build()
    by = sal.groupby([sal.season, sal.player.map(prep.norm)]).salary.max().to_dict()

    def cost(name, placed, end):
        n, total = prep.norm(name), 0.0
        for y in range(placed.year - 1, end.year + 1):
            w0, w1 = pd.Timestamp(f"{y}-10-20"), pd.Timestamp(f"{y + 1}-04-12")
            total += by.get((y, n), 0) * max((min(end, w1) - max(placed, w0)).days, 0) / (w1 - w0).days
        return total
    return cost


def headshot(pid, d=28):
    """Round photo (nba.com headshot, cached in data/headshots/); grey disc if unavailable."""
    D, path = d * S, None
    tile = Image.new("RGBA", (D, D), (219, 214, 200, 255))
    try:
        # ids can arrive as floats (1627749.0): the CDN then answers 200 with a generic grey silhouette
        path = Path(f"data/headshots/{int(pid)}.png")
        if not path.exists():
            r = requests.get(f"https://cdn.nba.com/headshots/nba/latest/260x190/{path.stem}.png", headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            r.raise_for_status()
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(r.content)
            Image.open(path).verify()
        tile.alpha_composite(Image.open(path).convert("RGBA").crop((62, 0, 197, 135)).resize((D, D), Image.Resampling.LANCZOS))  # tight on the face
    except Exception as e:  # noqa: BLE001
        print("no photo for", pid, "-", e)
        if path:
            path.unlink(missing_ok=True)
    m = Image.new("L", (D * 4, D * 4), 0)
    ImageDraw.Draw(m).ellipse([0, 0, D * 4 - 1, D * 4 - 1], fill=255)
    tile.putalpha(m.resize((D, D), Image.Resampling.LANCZOS))
    return tile


def scene_acl(inj, tab, g, stats):
    ts = tears(inj, g)
    spans = [(b - p).days for _, p, b, _ in ts if b is not None]
    unknown = [t for t in ts if t[2] is None]
    med = int(pd.Series(spans).median())
    longest = max(spans)
    longest_name = next(short(n) for n, p, b, _ in ts if b is not None and (b - p).days == longest)

    d0, d1 = pd.Timestamp("2018-10-01"), pd.Timestamp("2023-10-01")
    X0, X1 = 190, 690
    xs = lambda t: X0 + (X1 - X0) * (t - d0).days / (d1 - d0).days
    img, d = new_page("Torn ACLs (knee ligament)", f"{len(ts)} tears · {stats['period']} · from injury to first game back")
    for y in range(2018, 2023):  # season columns
        x = xs(pd.Timestamp(f"{y}-10-01"))
        d.text(((x + xs(pd.Timestamp(f"{y + 1}-10-01"))) / 2 * S, 124 * S), f"{y}-{str(y + 1)[2:]}", font=font(BOLD, 12), fill=GREY, anchor="ms")
        d.line([x * S, 132 * S, x * S, 690 * S], fill=(200, 197, 187), width=S)
    d.line([X1 * S, 132 * S, X1 * S, 690 * S], fill=(200, 197, 187), width=S)
    ROW0, STEP, BH = 150, 40, 22
    rows = []
    for i, (name, placed, back, pid) in enumerate(ts):
        y = ROW0 + i * STEP
        d.text((134 * S, (y + BH / 2) * S), short(name), font=font(BOLD, 14), fill=RED if back is None else INK, anchor="rm")
        tile = headshot(pid, 34)
        img.paste(tile, (round(144 * S), round((y + BH / 2 - 17) * S)), tile)
        rows.append((xs(placed), xs(back if back is not None else END), y, back is None))
    xe = xs(END)
    d.line([xe * S, 132 * S, xe * S, 700 * S], fill=INK, width=2 * S)
    d.rounded_rectangle([(xe - 60) * S, 702 * S, (xe + 60) * S, 726 * S], radius=5 * S, fill=INK)
    d.text((xe * S, 714 * S), "end of data", font=font(BOLD, 13), fill="white", anchor="mm")
    d.text((60 * S, 790 * S), f"{med} days", font=font(SLAB, 34), fill=BLUE, anchor="ls")
    d.text((60 * S, 814 * S), f"median absence, ≈ {round(med / 30.4)} months", font=font(BOLD, 14), fill=GREY, anchor="ls")
    if unknown:
        d.text((690 * S, 790 * S), f"{len(unknown)} unknown returns", font=font(SLAB, 34), fill=RED, anchor="rs")
        d.text((690 * S, 814 * S), "no game played afterwards in the data", font=font(BOLD, 14), fill=GREY, anchor="rs")
    else:
        d.text((690 * S, 790 * S), f"{longest} days", font=font(SLAB, 34), fill=RED, anchor="rs")
        d.text((690 * S, 814 * S), f"longest: {longest_name}", font=font(BOLD, 14), fill=GREY, anchor="rs")
    d.text((360 * S, 864 * S), "injury = placed on the injured list · return = first game played", font=font(BOLD, 13), fill=GREY, anchor="ms")
    d.text((360 * S, 884 * S), "photos: nba.com · source: Pro Sports Transactions (via Kaggle)" + (" · red: unknown return" if unknown else ""),
           font=font(REG, 12), fill=GREY, anchor="ms")

    STAG, DUR, HOLD = 3, 12, 60
    box_at = len(rows) * STAG + DUR
    box = [f"≈ ${fm(stats['acl_cost'])}M", f"in salaries · {len(ts)} tears,", f"{f1(stats['share_inj'])}% of injuries,", f"{f1(stats['share_days'])}% of days missed"]
    frames = []
    for f in range(box_at + 10 + HOLD):
        im = img.copy()
        d = ImageDraw.Draw(im)
        for i, (xa, xb, y, red) in enumerate(rows):
            p = ease((f - 4 - i * STAG) / DUR)
            if p > 0:
                d.rounded_rectangle([xa * S, y * S, max(xa + (xb - xa) * p, xa + 4) * S, (y + BH) * S], radius=4 * S, fill=RED if red else BLUE)
                if red and p >= 1:
                    d.text(((xb + 8) * S, (y + BH / 2) * S), "?", font=font(BOLD, 15), fill=RED, anchor="lm")
        a = min(max((f - box_at) / 10, 0), 1)
        if a > 0:
            layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            al = round(255 * a)
            ld.rounded_rectangle([440 * S, 138 * S, 706 * S, 250 * S], radius=10 * S, fill=DARKRED + (al,))
            ld.text((573 * S, 172 * S), box[0], font=font(SLAB, 30), fill=(255, 255, 255, al), anchor="mm")
            for j, line in enumerate(box[1:]):
                ld.text((573 * S, (200 + j * 18) * S), line, font=font(BOLD, 14), fill=(255, 255, 255, al), anchor="mm")
            im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
        frames.append(final(im))
    return frames


# ============================== scene 3: what the knee costs ==============================
def scene_knee(stats):
    img, _ = new_page("The knee, the costliest injury", f"{stats['from']} – {stats['to']} · seasons 2018-19 to 2022-23")
    lines = [  # (text, font, size, colour, y, appears at frame)
        ("in salaries paid during", BOLD, 30, INK, 520, 34),
        (f"{stats['knee_days']:,} days missed with knee injuries", BOLD, 30, INK, 566, 40),
        (f"of which ≈ ${fm(stats['acl_cost'])}M for {stats['acl_n']} torn ACLs", BOLD, 25, DARKRED, 650, 48),
        (f"only {f1(stats['share_inj'])}% of injuries, but {f1(stats['share_days'])}% of days missed", BOLD, 18, GREY, 692, 56),
    ]
    d = ImageDraw.Draw(img)
    d.text((360 * S, 864 * S), "season salary pro-rated over days on the injured list (regular season)", font=font(BOLD, 13), fill=GREY, anchor="ms")
    d.text((360 * S, 884 * S), "estimate · salaries: HoopsHype · source: Pro Sports Transactions (via Kaggle)", font=font(REG, 12), fill=GREY, anchor="ms")
    frames = []
    for f in range(56 + 8 + 65):
        im = img.copy()
        d = ImageDraw.Draw(im)
        if f >= 4:
            d.text((360 * S, 350 * S), f"≈ ${fm(stats['knee_cost'] * ease((f - 4) / 26))}M", font=font(SLAB, 100), fill=DARKRED, anchor="mm")
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for text, fn, size, col, y, at in lines:
            a = min(max((f - at) / 6, 0), 1)
            if a > 0:
                ld.text((360 * S, y * S), text, font=font(fn, size), fill=col + (round(255 * a),), anchor="mm")
        frames.append(final(Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")))
    return frames


# ============================== scene 4: top 3 franchises ==============================
LOGO = {  # franchise nickname -> ESPN team code (logo PNGs, cached in data/logos/)
    "Hawks": "atl", "Celtics": "bos", "Nets": "bkn", "Hornets": "cha", "Bulls": "chi", "Cavaliers": "cle", "Mavericks": "dal", "Nuggets": "den",
    "Pistons": "det", "Warriors": "gs", "Rockets": "hou", "Pacers": "ind", "Clippers": "lac", "Lakers": "lal", "Grizzlies": "mem", "Heat": "mia",
    "Bucks": "mil", "Timberwolves": "min", "Pelicans": "no", "Knicks": "ny", "Thunder": "okc", "Magic": "orl", "76ers": "phi", "Suns": "phx",
    "Blazers": "por", "Kings": "sac", "Spurs": "sa", "Raptors": "tor", "Jazz": "utah", "Wizards": "wsh",
}


def logo(nickname, size):
    """Franchise logo (RGBA, `size` px at output scale), downloaded once from ESPN's CDN; None if unavailable."""
    code = LOGO[nickname]
    path = Path(f"data/logos/{code}.png")
    try:
        if not path.exists():
            r = requests.get(f"https://a.espncdn.com/i/teamlogos/nba/500/{code}.png", headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            r.raise_for_status()
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(r.content)
            Image.open(path).verify()
        return Image.open(path).convert("RGBA").resize((size * S, size * S), Image.Resampling.LANCZOS)
    except Exception as e:  # noqa: BLE001
        print("no logo for", nickname, "-", e)
        path.unlink(missing_ok=True)


def scene_franchises(rank, period):
    top = rank.head(3)
    gap = 100 * (1 - rank.days.iloc[4] / rank.days.iloc[0])  # how close the 5th is to the 1st
    img, d = new_page("The 3 most injured franchises", f"cumulative days missed · {period}")
    d.text((360 * S, 864 * S), "injury = placed on the injured list · only injuries with a known body part", font=font(BOLD, 13), fill=GREY, anchor="ms")
    d.text((360 * S, 884 * S), "source: Pro Sports Transactions (via Kaggle) · franchises grouped under their current name", font=font(REG, 12), fill=GREY, anchor="ms")
    BARW, X, STAG, DUR, HOLD = 340, 204, 10, 16, 60
    logos = [logo(r.franchise, 76) for r in top.itertuples()]
    note_at = 4 + 3 * STAG + DUR
    frames = []
    for f in range(note_at + 8 + HOLD):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for i, r in enumerate(top.itertuples()):
            y, p = 215 + i * 190, ease((f - 4 - i * STAG) / DUR)
            if p <= 0:
                continue
            al, col = round(255 * p), (DARKRED if i == 0 else RED)
            ld.text((30 * S, (y + 22) * S), str(i + 1), font=font(SLAB, 96), fill=(DARKRED if i == 0 else INK) + (al,), anchor="lm")
            if logos[i] is not None:
                t = logos[i].copy()
                t.putalpha(t.getchannel("A").point(lambda v: round(v * p)))
                layer.alpha_composite(t, (round(106 * S), round((y - 14) * S)))
            ld.text((X * S, y * S), r.name, font=font(BOLD, 28), fill=INK + (al,), anchor="ls")
            w = BARW * r.days / top.days.iloc[0] * p
            ld.rounded_rectangle([X * S, (y + 14) * S, (X + w) * S, (y + 46) * S], radius=4 * S, fill=col + (255,))
            ld.text(((X + BARW + 14) * S, (y + 32) * S), f"{round(r.days * p):,}", font=font(SLAB, 34), fill=col + (al,), anchor="lm")
            ld.text((X * S, (y + 70) * S), f"{r.injuries} injuries · {r.days / r.injuries:.0f} days on average", font=font(BOLD, 15), fill=GREY + (al,), anchor="ls")
        a = ease((f - note_at) / 8)
        if a > 0:
            al = round(255 * a)
            ld.text((360 * S, 770 * S), f"Very tight podium: #5 is within {gap:.0f}% of #1", font=font(BOLD, 22), fill=DARKRED + (al,), anchor="mm")
            ld.text((360 * S, 802 * S), "the ranking changes with the period or scope chosen", font=font(BOLD, 15), fill=GREY + (al,), anchor="mm")
        frames.append(final(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")))
    return frames


def main(out="body_map.gif"):
    inj = bm.injuries()
    tab = bm.by_region(inj)
    g, cost = games(), make_cost()
    inj["cost"] = [cost(p, a, e) if r in bm.LABEL else 0.0 for p, a, e, r in zip(inj.player, inj.placed, inj.end, inj.region)]
    by_cost = inj.groupby("region").cost.sum().sort_values(ascending=False)
    print((by_cost / 1e6).round(1).head(5).to_string())
    assert by_cost.index[0] == "knee", "the knee is not the costliest body part: change the slide title"
    acl = inj[inj.note.str.contains(ACL)]
    stats = {
        "knee_cost": by_cost["knee"], "knee_days": int(tab[tab.region == "knee"].days.iloc[0]),
        "acl_cost": acl.cost.sum(), "acl_n": len(tears(inj, g)),
        "share_inj": 100 * len(acl) / tab.injuries.sum(), "share_days": 100 * acl.days.sum() / tab.days.sum(),
    }
    print({k: round(v, 1) for k, v in stats.items()})
    stats.update({"from": fdate(inj.placed.min()), "to": fdate(inj.placed.max()), "period": f"{fdate(inj.placed.min(), False)} – {fdate(inj.placed.max(), False)}"})
    inj_all = bm.injuries(range(2010, 2023))  # franchise ranking: since 2010-11
    rank = bm.by_franchise(inj_all)
    print(rank.head(6)[["franchise", "days", "injuries"]].to_string())
    period_all = f"{fdate(inj_all.placed.min())} – {fdate(inj_all.placed.max())}"
    a, b, c, e = scene_body(inj, tab, g), scene_acl(inj, tab, g, stats), scene_knee(stats), scene_franchises(rank, period_all)
    fade = lambda x, y, n: [Image.blend(x, y, (i + 1) / (n + 1)) for i in range(n)]
    frames = a + fade(a[-1], b[0], 8) + b + fade(b[-1], c[0], 8) + c + fade(c[-1], e[0], 8) + e + fade(e[-1], a[0], 8)  # loops back to the empty body
    builder = GIFBuilder(W, H, FPS)
    builder.add_frames(frames)
    return builder.save(out, num_colors=128)


if __name__ == "__main__":
    main()
