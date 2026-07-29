import sys; sys.path.insert(0,".")
from pathlib import Path
from PIL import Image
from app.services.compositor import LightContract, erode_alpha, relight, trim_alpha
from app.services.likeness import measure
L=Path("source_material/imported_canon/character_layers")
R=Path("characters/working/repaired_layers")
SC=dict(a=90.0,k=(150,225,235),f=(30,70,80),s=(40,90,100))
rows=[]
for lp in sorted(L.glob("*/*.png")):
    rel=lp.relative_to(L).as_posix()
    use=R/rel if (R/rel).is_file() else lp
    im=erode_alpha(trim_alpha(Image.open(use).convert("RGBA")),1)
    light=LightContract(key_angle_deg=SC["a"],key_color=SC["k"],fill_color=SC["f"],
        key_strength=0.22,fill_strength=0.10,rim_strength=0.10,
        spill_strength=0.14,protect_neutrals=0.85)
    r=measure(relight(im,light,spill_color=SC["s"]),use,"X")
    rows.append((r.score,r.palette_score,r.feature_legibility_score,r.contamination_score,
                 im.height,rel,r.passed))
import collections
reasons=collections.Counter()
for s,pal,leg,con,h,rel,ok in rows:
    if ok: continue
    if pal<92: reasons["palette drift"]+=1
    elif leg<85: reasons["legibility (too small)"]+=1
    elif con<99: reasons["contamination"]+=1
    else: reasons[f"overall<95 only"]+=1
print(f"layers: {len(rows)}  pass: {sum(1 for r in rows if r[6])}")
for k,v in reasons.most_common(): print(f"  {v:4d}  {k}")
print("\nworst 12 (score, palette, legibility, height):")
for s,pal,leg,con,h,rel,ok in sorted(rows)[:12]:
    print(f"  {s:5.1f}  pal{pal:6.1f}  leg{leg:6.1f}  h{h:5d}  {rel}")
print("\nheight distribution of failures:")
hs=[h for s,pal,leg,con,h,rel,ok in rows if not ok]
if hs: print(f"  min {min(hs)}  median {sorted(hs)[len(hs)//2]}  max {max(hs)}")
