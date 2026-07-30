"""
Banana Lab 2.0 - consolidated aesthetic scorecard.

Eight scored properties plus one guardrail, all of which survived independent
sceptical attack, measured from a rendered page image alone. No repo imports, no
network, no hand-placed rects, no hand-read windows.

Discarded here and NOT computed: accent_blob_share (45% of published accent
islands are lettering; art-only AUC 0.713; seed noise / gap = 1.93),
accent_lift_L (AUC 0.333; the approved cast is achromatic), flat_fill_share
(r = +0.948 with share_in_large_shapes; measures blur, not cel fills),
outline_weight p50 (published 0.96-2.15 pt fully contains current 0.96-1.92),
offpanel_printed_matter (0.000 on 14/20 published and on the current pages),
lead_figure_share_of_panel_height (published 0.464 vs current 0.424),
rule_mm (current 0.847 sits inside the published [0.339, 2.032]),
ground_chroma univariate (B06 is 0.000, identical to the current pages),
portrait_share and median_panel_aspect (do not separate under an automatic
segmenter: 11/20 and 10/20 published pages inside the current range), and
n_panels / largest_panel_share (they separate, but the target is blocked by
FORMAT_STANDARD.md, so they are a conflict to record, not a metric to chase).

Measurement contract
--------------------
Input is ONE page rendered at 300 dpi as an HxWx3 uint8 sRGB array.
  - 300 dpi is mandatory. hairline_ink_density is NOT dpi-invariant (doubling
    render dpi moved published page values +3%..+162%, median +26%), and the
    rule-weight scan windows are expressed in inches of the render.
  - The lettering detector is calibrated at 110 dpi, so score_page() downsamples
    internally. Do not feed it a 110 dpi page directly.
  - Both published PDFs are natively 5100x6599 on a 612x792 pt page = 600 dpi,
    so 300 dpi is a clean 2x downsample of the published side, not an upsample.

Two panel segmenters are used, each only where it was validated:
  panel_components()   border flood-fill, has an explicit full-bleed fallback.
                       Used for geometry, line and colour properties.
  ground_and_panels()  smooth-page-ground model. Used for the two furniture
                       properties that are *about* the page ground.

Usage
-----
    python scorecard.py            # runs the full published-vs-current study
    from scorecard import score_page, TARGETS
    score_page(rgb_300dpi)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

DPI = 300.0
LETTER_DPI = 110.0

# ---------------------------------------------------------------- colour maths
_M = np.array([[.4124564, .3575761, .1804375],
               [.2126729, .7151522, .0721750],
               [.0193339, .1191920, .9503041]])
_WP = np.array([.95047, 1., 1.08883])


def srgb_to_lab(rgb):
    a = np.asarray(rgb, np.float64) / 255.0
    lin = np.where(a <= .04045, a / 12.92, ((a + .055) / 1.055) ** 2.4)
    xyz = lin @ _M.T / _WP
    e, k = 216 / 24389, 24389 / 27
    f = np.where(xyz > e, np.cbrt(xyz), (k * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16,
                     500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], -1)


def _chroma(lab):
    return np.hypot(lab[..., 1], lab[..., 2])


WHITE_LAB = srgb_to_lab(np.array([255.0, 255.0, 255.0]))


def _disk(px):
    px = max(3, int(round(px)) | 1)
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (px, px))


# ------------------------------------------------- segmenter 1: flood-fill art
def panel_components(rgb, dpi=DPI):
    """Panel interiors by flooding the page ground in from the border.

    Returns (art_mask, [per-panel masks], [per-panel bboxes], diag).
    On a full-bleed page the whole page becomes one panel, which is the
    correct reading for a cover.
    """
    h, w = rgb.shape[:2]
    small = cv2.resize(rgb, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    g = np.zeros((sh + 2, sw + 2), np.uint8)
    work = small.copy()
    seeds = ([(x, 0) for x in range(0, sw, 8)] + [(x, sh - 1) for x in range(0, sw, 8)] +
             [(0, y) for y in range(0, sh, 8)] + [(sw - 1, y) for y in range(0, sh, 8)])
    for sx, sy in seeds:
        if g[sy + 1, sx + 1]:
            continue
        cv2.floodFill(work, g, (sx, sy), 0, (6,) * 3, (6,) * 3,
                      cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (1 << 8))
    lbl, n = ndi.label(~g[1:-1, 1:-1].astype(bool))
    keep = np.zeros(n + 1, bool)
    kept, fills, areas = [], [], []
    for i in range(1, n + 1):
        sel = lbl == i
        a = int(sel.sum())
        if a <= 0.02 * sh * sw:
            continue
        keep[i] = True
        kept.append(i)
        ys, xs = np.where(sel)
        fills.append(a / ((ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)))
        areas.append(a)
    rect = float(np.average(fills, weights=areas)) if areas else 0.0
    m = cv2.resize(keep[lbl].astype(np.uint8), (w, h),
                   interpolation=cv2.INTER_NEAREST).astype(bool)
    fullbleed = bool(rect < 0.85 or m.mean() < 0.10)
    er = _disk(0.045 * dpi)
    if fullbleed:
        m = np.ones((h, w), bool)
        art = cv2.erode(m.astype(np.uint8), er).astype(bool)
        comps, boxes = [art], [(0, 0, w, h)]
    else:
        art = cv2.erode(m.astype(np.uint8), er).astype(bool)
        comps, boxes = [], []
        for i in kept:
            ci = cv2.resize((lbl == i).astype(np.uint8), (w, h),
                            interpolation=cv2.INTER_NEAREST)
            ys, xs = np.where(ci.astype(bool))
            boxes.append((int(xs.min()), int(ys.min()),
                          int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)))
            comps.append(cv2.erode(ci, er).astype(bool))
    return art, comps, boxes, dict(rect=rect, fullbleed=fullbleed,
                                   n_panels=len(comps), page_share=float(m.mean()))


# ------------------------------------------- segmenter 2: smooth page ground
def _sd(p, k=5):
    m = ndi.uniform_filter(p, k, mode="nearest")
    m2 = ndi.uniform_filter(p * p, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0))


def ground_and_panels(lab, panel_min=0.02):
    h, w = lab.shape[:2]
    smooth = (_sd(lab[..., 0]) < 2.) & (_sd(lab[..., 1]) < 2.) & (_sd(lab[..., 2]) < 2.)
    lbl, n = ndi.label(smooth)
    b = np.zeros((h, w), bool)
    b[0, :] = b[-1, :] = b[:, 0] = b[:, -1] = True
    ids = set(np.unique(lbl[b & smooth])) - {0}
    ground = np.isin(lbl, list(ids)) if ids else np.zeros((h, w), bool)
    holes, m = ndi.label(~ground)
    rects = []
    for i in range(1, m + 1):
        msk = holes == i
        if msk.sum() / (h * w) < panel_min:
            continue
        sr, sc = msk.sum(1), msk.sum(0)
        kr = np.where(sr >= .88 * sr.max())[0]
        kc = np.where(sc >= .88 * sc.max())[0]
        if kr.size < 8 or kc.size < 8:
            continue
        rects.append((int(kc.min()), int(kr.min()), int(kc.max()), int(kr.max())))
    return ground, rects


# ============================================================ P1  panel rule
def panel_rule(rgb, dpi=DPI):
    """Colour and weight of the ink rule bounding each panel.

    Scans outward-to-inward across each panel edge from the page ground,
    finds the first step > dE 12, walks to the plateau, and measures the
    plateau's Lab and width. Rule L* is orthogonal to page brightness
    (r = -0.089 across the 20 published pages), so it is not a darkness proxy.
    """
    lab = srgb_to_lab(rgb)
    h, w = lab.shape[:2]
    _, rects = ground_and_panels(lab)
    OUT = max(8, int(.15 * dpi))
    IN = max(12, int(.24 * dpi))
    cols, thick = [], []
    for x0, y0, x1, y1 in rects:
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        scans = []
        if y0 - OUT >= 0:
            scans.append(lab[y0 - OUT:y0 + IN, cx])
        if y1 + OUT < h:
            scans.append(lab[y1 + OUT:max(0, y1 - IN):-1, cx])
        if x0 - OUT >= 0:
            scans.append(lab[cy, x0 - OUT:x0 + IN])
        if x1 + OUT < w:
            scans.append(lab[cy, x1 + OUT:max(0, x1 - IN):-1])
        for s in scans:
            if len(s) < OUT + 8:
                continue
            base = s[:max(4, OUT // 4)].mean(0)
            d = np.linalg.norm(s - base, axis=-1)
            if not (d > 12).any():
                continue
            i = int(np.argmax(d > 12))
            if i < max(3, OUT // 8) or i > len(s) - 6:
                continue
            j = i
            while j + 1 < len(s) and np.linalg.norm(s[j + 1] - s[j]) > 4.:
                j += 1
            seed = s[j]
            t = 1
            while j + t < len(s) and np.linalg.norm(s[j + t] - seed) < 18.:
                t += 1
            if (j - i) + t > .2 * dpi:
                continue
            cols.append(s[j:j + t].mean(0))
            thick.append((j - i) + t)
    if not cols:
        return dict(rule_L=None, rule_chroma=None, rule_mm=None, rule_edges=0)
    a = np.array(cols)
    return dict(rule_edges=len(cols),
                rule_L=round(float(np.median(a[:, 0])), 2),
                rule_chroma=round(float(np.median(np.hypot(a[:, 1], a[:, 2]))), 2),
                rule_mm=round(float(np.median(thick)) / dpi * 25.4, 3))


# ====================================================== P2  page-ground board
def page_ground(rgb):
    """Lightness of the printed board the panels sit on.

    Sampled from the 2%-of-trim ring minus any detected panel. Reported per
    page; the published TARGET is stated per distinct board, because edition A
    prints one board on 9 of its 11 pages and a per-page median just counts
    that reuse.
    """
    lab = srgb_to_lab(rgb)
    h, w = lab.shape[:2]
    ground, rects = ground_and_panels(lab)
    ring = np.zeros((h, w), bool)
    b = max(4, int(.02 * min(h, w)))
    ring[:b, :] = ring[-b:, :] = ring[:, :b] = ring[:, -b:] = True
    for x0, y0, x1, y1 in rects:
        ring[y0:y1 + 1, x0:x1 + 1] = False
    gm = ring & ground
    if gm.sum() < 200:
        gm = ring
    if not gm.any():
        return dict(ground_L=None, ground_chroma=None, ground_share_pct=0.0)
    return dict(ground_L=round(float(np.median(lab[..., 0][gm])), 2),
                ground_chroma=round(float(np.median(_chroma(lab)[gm])), 2),
                ground_share_pct=round(float(ground.sum()) / (h * w) * 100, 2))


# ==================================================== P3  lettering coverage
_GH = (4, 34)
_STROKE = 4.2
_HCV = .45
_BSD = .40
_PERLINE = 4
_MING = 8
_ASPECT = 2.2
_FLAT = 1.20
_SURR = 10.
_CAP = .12


def _rob(x):
    m = np.median(x)
    return float(1.4826 * np.median(np.abs(x - m)))


def _glyphs(L, pol, bg):
    diff = (bg - L) if pol == "dark" else (L - bg)
    mask = ndi.binary_opening(diff > 20., np.ones((2, 2)))
    lbl, _ = ndi.label(mask)
    out = []
    for i, sl in enumerate(ndi.find_objects(lbl), 1):
        if sl is None:
            continue
        by, bx = sl
        hh, ww = by.stop - by.start, bx.stop - bx.start
        if not (_GH[0] <= hh <= _GH[1] and 1 <= ww <= 44):
            continue
        sub = lbl[sl] == i
        if not (5 <= int(sub.sum()) <= 700):
            continue
        if float(ndi.distance_transform_edt(np.pad(sub, 1)).max()) > _STROKE:
            continue
        out.append(dict(x0=bx.start, y0=by.start, x1=bx.stop, y1=by.stop, h=hh, w=ww,
                        cy=(by.start + by.stop) / 2, cx=(bx.start + bx.stop) / 2))
    return out, mask


def _line_ok(run):
    hs = np.array([g["h"] for g in run], float)
    if hs.mean() <= 0 or hs.std() / hs.mean() > _HCV:
        return False
    if _rob(np.array([g["y1"] for g in run], float)) > _BSD * float(np.median(hs)):
        return False
    return (max(g["x1"] for g in run) - min(g["x0"] for g in run)) >= _ASPECT * float(np.median(hs))


def _lines(gs):
    if not gs:
        return []
    mh = float(np.median([g["h"] for g in gs]))
    gs = sorted(gs, key=lambda g: g["cy"])
    bands, cur = [], [gs[0]]
    for g in gs[1:]:
        if abs(g["cy"] - cur[-1]["cy"]) <= .5 * mh:
            cur.append(g)
        else:
            bands.append(cur)
            cur = [g]
    bands.append(cur)
    lines = []
    for band in bands:
        band = sorted(band, key=lambda g: g["cx"])
        mw = float(np.median([g["w"] for g in band]))
        run = [band[0]]
        for g in band[1:]:
            if g["x0"] - run[-1]["x1"] <= max(4., 1.8 * mw):
                run.append(g)
            else:
                if len(run) >= _PERLINE and _line_ok(run):
                    lines.append(run)
                run = [g]
        if len(run) >= _PERLINE and _line_ok(run):
            lines.append(run)
    return lines


def _blocks(lines):
    recs = [dict(x0=min(g["x0"] for g in ln), x1=max(g["x1"] for g in ln),
                 y0=min(g["y0"] for g in ln), y1=max(g["y1"] for g in ln),
                 n=len(ln), h=float(np.median([g["h"] for g in ln])), glyphs=ln)
            for ln in lines]
    recs.sort(key=lambda r: r["y0"])
    used = [False] * len(recs)
    out = []
    for i, r in enumerate(recs):
        if used[i]:
            continue
        cur = [r]
        used[i] = True
        go = True
        while go:
            go = False
            cx0 = min(c["x0"] for c in cur)
            cx1 = max(c["x1"] for c in cur)
            cy1 = max(c["y1"] for c in cur)
            ch = float(np.median([c["h"] for c in cur]))
            for j, s in enumerate(recs):
                if used[j]:
                    continue
                ov = min(cx1, s["x1"]) - max(cx0, s["x0"])
                if ov <= 0 or ov / max(1, min(cx1 - cx0, s["x1"] - s["x0"])) < .35:
                    continue
                if s["y0"] - cy1 > 1.9 * ch or abs(s["h"] - ch) > .5 * ch:
                    continue
                cur.append(s)
                used[j] = True
                go = True
        out.append(cur)
    return out


def lettering_coverage(rgb110):
    """Share of page occupied by balloon / caption CONTAINERS.

    A container qualifies only if it holds >=8 glyph-shaped components forming
    >=1 baseline-consistent line, its fill is locally flat (robust MAD < 1.2 in
    all three Lab channels), it is a filled convex-ish region (fill >= 0.45),
    and its fill differs from its immediate surround by dE >= 10.
    Controls: 0 containers on 11/11 textless generated plates.
    Known bias: recall is 77-89% of true container area on audited pages and 0%
    on one rotated baseline, so published values are a FLOOR.
    """
    lab = srgb_to_lab(rgb110)
    h, w = lab.shape[:2]
    area_pg = h * w
    L = lab[..., 0]
    bg = ndi.median_filter(L, 21, mode="nearest")
    res = [L - bg] + [lab[..., k] - ndi.median_filter(lab[..., k], 21, mode="nearest")
                      for k in (1, 2)]
    dxa = np.zeros((h, w))
    dya = np.zeros((h, w))
    sx = np.linalg.norm(np.diff(lab, axis=1), axis=-1)
    sy = np.linalg.norm(np.diff(lab, axis=0), axis=-1)
    dxa[:, :-1] = sx
    dxa[:, 1:] = np.maximum(dxa[:, 1:], sx)
    dya[:-1, :] = sy
    dya[1:, :] = np.maximum(dya[1:, :], sy)
    edge = np.maximum(dxa, dya) > 10.
    found = []
    for pol in ("dark", "light"):
        gs, gmask = _glyphs(L, pol, bg)
        for blk in _blocks(_lines(gs)):
            if sum(b["n"] for b in blk) < _MING:
                continue
            x0 = min(b["x0"] for b in blk)
            x1 = max(b["x1"] for b in blk)
            y0 = min(b["y0"] for b in blk)
            y1 = max(b["y1"] for b in blk)
            lh = float(np.median([b["h"] for b in blk]))
            pad = max(3, int(round(.55 * lh)))
            px0, py0 = max(0, x0 - pad), max(0, y0 - pad)
            px1, py1 = min(w, x1 + pad), min(h, y1 + pad)
            reg = (slice(py0, py1), slice(px0, px1))
            field = ~ndi.binary_dilation(gmask[reg], np.ones((3, 3)), 2)
            if field.sum() < 60:
                continue
            if max(_rob(res[k][reg][field]) for k in range(3)) > _FLAT:
                continue
            fill = np.array([np.median(lab[..., k][reg][field]) for k in range(3)])
            mrg = int(max(4 * lh, 3 * pad))
            ox0, oy0 = max(0, px0 - mrg), max(0, py0 - mrg)
            ox1, oy1 = min(w, px1 + mrg), min(h, py1 + mrg)
            win = lab[oy0:oy1, ox0:ox1]
            near = ~edge[oy0:oy1, ox0:ox1]
            br = np.zeros((h, w), bool)
            for rec in blk:
                for g in rec["glyphs"]:
                    br[g["y0"]:g["y1"], g["x0"]:g["x1"]] = True
            near |= ndi.binary_dilation(br[oy0:oy1, ox0:ox1], np.ones((3, 3)), 1)
            seed = np.zeros(near.shape, bool)
            seed[py0 - oy0:py1 - oy0, px0 - ox0:px1 - ox0] = field
            cl, cn = ndi.label(near)
            if cn == 0:
                continue
            ids, cnt = np.unique(cl[seed & (cl > 0)], return_counts=True)
            if ids.size == 0:
                continue
            cont = ndi.binary_fill_holes(cl == ids[cnt.argmax()])
            a = float(cont.sum())
            if a / area_pg > _CAP or a < .6 * field.sum():
                continue
            ys, xs = np.where(cont)
            if a / ((ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)) < .45:
                continue
            ring = ndi.binary_dilation(cont, np.ones((3, 3)), 3) & ~cont
            if ring.sum() < 60:
                continue
            if float(np.linalg.norm(fill - np.median(win[ring], axis=0))) < _SURR:
                continue
            found.append(dict(bbox=[int(ox0 + xs.min()), int(oy0 + ys.min()),
                                    int(ox0 + xs.max() + 1), int(oy0 + ys.max() + 1)],
                              area=int(a), area_pct=a / area_pg * 100))
    found.sort(key=lambda f: -f["area"])
    keep = []
    for f in found:
        ax0, ay0, ax1, ay1 = f["bbox"]
        clash = False
        for g in keep:
            bx0, by0, bx1, by1 = g["bbox"]
            iw = min(ax1, bx1) - max(ax0, bx0)
            ih = min(ay1, by1) - max(ay0, by0)
            if iw > 0 and ih > 0 and iw * ih > .4 * f["area"]:
                clash = True
                break
        if not clash:
            keep.append(f)
    return dict(lettering_count=len(keep),
                lettering_pct=round(sum(k["area_pct"] for k in keep), 3))


# ============================== P4/P5  large flat shapes + hairline ink
_LARGE_SQIN = 0.05
_SHAPE_GRAD_DE = 6.0


def ink_mask(L, dpi=DPI):
    closed = cv2.morphologyEx(L.astype(np.float32), cv2.MORPH_CLOSE, _disk(0.14 * dpi))
    return (closed - L) > 18.0


def _local_lab_range(lab, dpi=DPI, win_in=0.017):
    k = _disk(win_in * dpi)
    acc = np.zeros(lab.shape[:2], np.float32)
    for c in range(3):
        ch = lab[..., c].astype(np.float32)
        acc += (cv2.dilate(ch, k) - cv2.erode(ch, k)) ** 2
    return np.sqrt(acc)


def graphic_mass(rgb, art, lab=None, local_de=None, dpi=DPI):
    """share_in_large_shapes and hairline_ink_density over one art region.

    share_in_large_shapes: fraction of the region lying inside a single flat
        colour cell of >= 0.05 sq in of PRINT, cells bounded by ink or by a
        local Lab range > 6. Cleared of brightness (+/-14 L* moves it <=0.02),
        lettering (excluding balloons moves the published median 0.558->0.550)
        and source-resolution (published handicapped to 109 px/printed-inch
        still 0.528-0.728) confounds. Needs sigma=6 px of blur to game, where
        hairline needs sigma=2.
    hairline_ink_density: inches of skeletonised ink stroke narrower than
        1.5 pt per square inch of print. Diagnostic only, and it must be read
        as a two-sided band: it falls with ANY blur or upscale, so a low value
        is not evidence of graphic simplification on its own.
    """
    if lab is None:
        lab = srgb_to_lab(rgb)
    if local_de is None:
        local_de = _local_lab_range(lab, dpi)
    L = lab[..., 0].astype(np.float32)
    ink = ink_mask(L, dpi) & art
    sqin = art.sum() / dpi / dpi
    if not art.any() or sqin <= 0:
        return dict(share_in_large_shapes=None, hairline_ink_density=None, sqin=0.0)
    if ink.any():
        dt = ndi.distance_transform_edt(ink)
        sk = skeletonize(ink)
        wpt = 2.0 * dt[sk] / dpi * 72.0
        hair = float((wpt < 1.5).sum()) / dpi / sqin
    else:
        hair = 0.0
    boundary = ink | (local_de > _SHAPE_GRAD_DE) | ~art
    cells, n = ndi.label(~boundary)
    if not n:
        large = 0.0
    else:
        sizes = np.bincount(cells.ravel())[1:]
        large = float(sizes[sizes >= _LARGE_SQIN * dpi * dpi].sum()) / float(art.sum())
    return dict(share_in_large_shapes=round(float(large), 4),
                hairline_ink_density=round(float(hair), 3),
                sqin=round(float(sqin), 2))


# ====================================== P6/P7  colour hierarchy per panel
_INK_L = 25.0
_WHITE_DE = 10.0


def _body(lab, mask):
    L = lab[..., 0]
    dw = np.linalg.norm(lab - WHITE_LAB, axis=-1)
    return mask & (L >= _INK_L) & (dw >= _WHITE_DE)


def colour_hierarchy(rgb, mask, lab=None):
    """peak_over_field, n_hue_families and the C_p95 guardrail, one panel.

    peak_over_field = P99 of chroma minus the median of a mask-aware
        Gaussian chroma field at sigma = 8% of panel height. A contrast
        statistic: neither term separates alone (P99 AUC 0.750, field AUC
        0.333 wrong way) but the difference does (AUC 0.833). Orthogonal to
        page darkness (r = +0.004 vs L_p50) and to ink (r = +0.069).
    n_hue_families = number of 10-degree hue bins holding > 5% of the panel's
        chroma mass. Construct-validated: snapping every chromatic pixel to K
        hue anchors makes it track K and saturate above ~4.
    C_p95 = 95th percentile chroma. NOT a separating property; carried as a
        GUARDRAIL, because the prompt edit that lands n_hue_families on target
        was measured to drag C_p95 from 61 to 42 against a published 63.
    Ink (L* < 25) and near-white (dE to white < 10) are excluded from all three.
    """
    if lab is None:
        lab = srgb_to_lab(rgb)
    L = lab[..., 0]
    C = _chroma(lab)
    body = _body(lab, mask)
    if int(body.sum()) < 4000:
        return dict(peak_over_field=None, n_hue_families=None, C_p95=None)
    ys, _ = np.where(mask)
    panel_h = ys.max() - ys.min() + 1
    sig = max(2.0, 0.08 * panel_h)
    f = np.where(mask, C, 0.0).astype(np.float32)
    num = cv2.GaussianBlur(f, (0, 0), sig)
    den = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sig)
    field = np.where(den > 1e-3, num / np.maximum(den, 1e-3), 0.0)
    Cb = C[body]
    pof = float(np.percentile(Cb, 99) - np.median(field[body]))

    sel = Cb >= 15.0
    if sel.sum() < 400:
        nh = None
    else:
        ab = lab[..., 1:][body][sel]
        hue = np.degrees(np.arctan2(ab[:, 1], ab[:, 0])) % 360.0
        hist = np.bincount((hue // 10).astype(int) % 36, weights=Cb[sel], minlength=36)
        nh = float(((hist / hist.sum()) > 0.05).sum())
    return dict(peak_over_field=round(pof, 2),
                n_hue_families=nh,
                C_p95=round(float(np.percentile(Cb, 95)), 2))


# ==================================================================== driver
def score_page(rgb300, dpi=DPI, want_panels=False):
    """Full scorecard for one page rendered at 300 dpi."""
    assert rgb300.ndim == 3 and rgb300.shape[2] == 3 and rgb300.dtype == np.uint8
    h, w = rgb300.shape[:2]
    lab = srgb_to_lab(rgb300)
    local_de = _local_lab_range(lab, dpi)
    art, comps, boxes, diag = panel_components(rgb300, dpi)

    out = dict(page_px=[int(w), int(h)], **diag)
    if diag["fullbleed"]:
        # A page whose art bleeds all four trim edges has no board and no rule.
        # Both instruments have a fallback path that would otherwise return a
        # confident number measured off the artwork, so they are nulled instead.
        out.update(rule_L=None, rule_chroma=None, rule_mm=None, rule_edges=0,
                   ground_L=None, ground_chroma=None, ground_share_pct=None)
    else:
        out.update(panel_rule(rgb300, dpi))
        out.update(page_ground(rgb300))

    s = LETTER_DPI / dpi
    rgb110 = cv2.resize(rgb300, (max(1, int(round(w * s))), max(1, int(round(h * s)))),
                        interpolation=cv2.INTER_AREA)
    out.update(lettering_coverage(rgb110))

    # per-panel line + colour properties, area-weighted to a page value
    per = []
    for m in comps:
        r = graphic_mass(rgb300, m, lab=lab, local_de=local_de, dpi=dpi)
        r.update(colour_hierarchy(rgb300, m, lab=lab))
        r["px"] = int(m.sum())
        per.append(r)

    def wavg(key):
        v = [(p[key], p["px"]) for p in per if p.get(key) is not None]
        if not v:
            return None
        vals = np.array([x[0] for x in v], float)
        wt = np.array([x[1] for x in v], float)
        return round(float(np.average(vals, weights=wt)), 4)

    for key in ("share_in_large_shapes", "hairline_ink_density",
                "peak_over_field", "n_hue_families", "C_p95"):
        out[key] = wavg(key)
    if want_panels:
        out["_panels"] = per
    return out


# Published targets and tolerances. Every target below is the median of the 20
# published pages AS MEASURED BY THIS FILE at 300 dpi - not a value carried over
# from another study. Tolerances are the published range, widened only where the
# instrument's own error is larger than the range.
TARGETS = {
    "rule_L":                dict(target=2.23,  tol="<= 10",           pub="[0.61, 17.56]"),
    "rule_chroma":           dict(target=1.26,  tol="<= 6",            pub="[0.16, 23.28]"),
    "ground_L":              dict(target=35.0,  tol="20 .. 66",        pub="[20.4, 65.9]",
                                  note="target is the median of the 8 DISTINCT boards. "
                                       "The per-page median of 55.6 only counts edition "
                                       "A reprinting one board on 9 of its 11 pages."),
    "lettering_pct":         dict(target=5.16,  tol=">= 2.0",          pub="[0.00, 12.00]",
                                  note="detector recall is 77-89% of true container "
                                       "area, so published values are a FLOOR. A09 "
                                       "reads 0.000 and is a known miss (rotated "
                                       "baseline), not an empty page."),
    "share_in_large_shapes": dict(target=0.558, tol=">= 0.26",         pub="[0.232, 0.793]"),
    "hairline_ink_density":  dict(target=2.65,  tol="0.4 .. 11.0",     pub="[0.48, 8.71]",
                                  note="TWO-SIDED and diagnostic only. Falls with any "
                                       "blur or upscale, so a low value is not "
                                       "evidence of graphic simplification. Upper "
                                       "bound is 12.81 at the published files' native "
                                       "600 dpi, hence 11.0 rather than 8.71."),
    "peak_over_field":       dict(target=54.60, tol="+/- 12",          pub="[28.7, 79.5]"),
    "n_hue_families":        dict(target=4.00,  tol="<= 5.5",          pub="[2.0, 9.0]"),
    "C_p95":                 dict(target=66.05, tol=">= 50",           pub="[31.2, 82.6]",
                                  note="GUARDRAIL, not a target. Does not separate "
                                       "(AUC 0.800, 2/20 inside the current range). "
                                       "Carried because the current output is already "
                                       "BELOW published peak chroma, so any change "
                                       "made to hit n_hue_families must not lower it."),
}

PDF_A = r"I:\MonkeyZoo Comic Strip\Fusion Squad\1\TheFusionSquad.pdf"
PDF_B = r"I:\MonkeyZoo Comic Strip\Fusion Squad\2\nft\FusionZoo The DeFusion Tapes.pdf"
CUR = (r"R:\BananaLab2.0\issues\issue-001-neonblue-the-last-light-of-summer"
       r"\09_composites\sample_pages")
CUR_FILES = ["page_00_cover.png", "page_01.png", "page_02.png"]
KEYS = ["rule_L", "rule_chroma", "ground_L", "lettering_pct",
        "share_in_large_shapes", "hairline_ink_density",
        "peak_over_field", "n_hue_families", "C_p95"]


def _pdf_pages(path, tag):
    import fitz
    d = fitz.open(path)
    for i in range(len(d)):
        p = d[i].get_pixmap(dpi=int(DPI))
        rgb = np.frombuffer(p.samples, np.uint8).reshape(
            p.height, p.width, p.n)[..., :3].copy()
        yield f"{tag}{i:02d}", rgb


def main():
    rows = []
    src = ([("PUB", n, r) for n, r in _pdf_pages(PDF_A, "A")] +
           [("PUB", n, r) for n, r in _pdf_pages(PDF_B, "B")])
    for f in CUR_FILES:
        bgr = cv2.imread(os.path.join(CUR, f), cv2.IMREAD_COLOR)
        src.append(("CUR", "CUR_" + f.replace(".png", "").replace("page_", "p"),
                    cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
    hdr = "%-4s %-10s " % ("pop", "page") + " ".join("%-8s" % k[:8] for k in KEYS)
    print(hdr)
    for pop, name, rgb in src:
        r = score_page(rgb)
        rows.append(dict(pop=pop, page=name, **{k: r.get(k) for k in KEYS}))
        cells = []
        for k in KEYS:
            v = r.get(k)
            cells.append("%-8s" % ("--" if v is None else
                                   ("%.3f" % v if isinstance(v, float) else str(v))))
        print("%-4s %-10s " % (pop, name) + " ".join(cells), flush=True)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "scorecard.json"), "w") as fh:
        json.dump(rows, fh, indent=1)

    print("\n%-24s %-34s %-24s %s" % ("property", "PUBLISHED med [min,max]",
                                      "CURRENT (story pages)", "separates"))
    for k in KEYS:
        pub = [r[k] for r in rows if r["pop"] == "PUB" and r[k] is not None]
        cur = [r[k] for r in rows if r["pop"] == "CUR" and r[k] is not None
               and r["page"] != "CUR_p00_cover"]
        if not pub or not cur:
            continue
        pub, cur = np.array(pub, float), np.array(cur, float)
        auc = float(np.mean([(p > c) + 0.5 * (p == c) for p in pub for c in cur]))
        # Two-sided. "inside" alone is misleading when the current range is a
        # single point: it reports 0 overlap by construction. "wrong side"
        # counts published pages on the far side of the whole current range,
        # which is what actually breaks a one-directional target.
        inside = int(((pub >= cur.min()) & (pub <= cur.max())).sum())
        below = int((pub < cur.min()).sum())
        above = int((pub > cur.max()).sum())
        wrong = above if np.median(pub) < np.median(cur) else below
        print("%-22s %-30s %-26s AUC %.3f in %d/%d wrong-side %d" % (
            k, "%.3f [%.3f, %.3f]" % (np.median(pub), pub.min(), pub.max()),
            "%.3f [%.3f, %.3f]" % (np.median(cur), cur.min(), cur.max()),
            auc, inside, len(pub), wrong))


if __name__ == "__main__":
    sys.exit(main())
