import sys; sys.path.insert(0,".")
import numpy as np
from pathlib import Path
from PIL import Image
from app.services.likeness import measure
from app.services.compositor import LightContract, relight
L=Path("characters/working/repaired_layers/neonblue/neonblue_16_worried.png")
if not L.is_file(): L=Path("source_material/imported_canon/character_layers/neonblue/neonblue_16_worried.png")
full=Image.open(L).convert("RGBA")
light=LightContract(key_angle_deg=90.0,key_color=(150,225,235),fill_color=(30,70,80),
                    key_strength=0.22,fill_strength=0.10,rim_strength=0.10,
                    spill_strength=0.14,protect_neutrals=0.85)
bad=0
def show(tag,img,cont=0,expect="FAIL"):
    global bad
    r=measure(img,L,"MZ-CHAR-005",contamination_px=cont)
    ok="PASS" if r.passed else "FAIL"
    wrong = ok!=expect
    if wrong: bad+=1
    print(f"  {tag:42s} {r.score:5.1f}  pal {r.palette_score:5.1f}  dE {r.palette_delta_e:5.1f}  {ok}{'   <-- WRONG' if wrong else ''}")
a=np.asarray(full).astype(int)
print("NEGATIVE CONTROLS (should FAIL):")
h=a.copy(); h[...,[0,1]]=h[...,[1,0]]
show("hue-swapped (R<->G)", Image.fromarray(h.astype(np.uint8),"RGBA"))
g=a.copy(); lum=(g[...,:3]*[0.2126,0.7152,0.0722]).sum(axis=2,keepdims=True); g[...,:3]=np.repeat(lum,3,axis=2)
show("fully desaturated", Image.fromarray(g.astype(np.uint8),"RGBA"))
show("free tint (no hue protection)", relight(full, LightContract(key_angle_deg=90.0,
     key_color=(150,225,235),fill_color=(30,70,80),key_strength=0.22,fill_strength=0.10,
     rim_strength=0.10,spill_strength=0.14,protect_neutrals=0.0), spill_color=(40,90,100)))
d=a.copy(); d[...,:3]=(d[...,:3]*0.25).astype(int)
show("crushed to 25% lightness", Image.fromarray(d.astype(np.uint8),"RGBA"))
show("clean + 6000px card bleed", relight(full,light,spill_color=(40,90,100)), cont=6000)
# targeted: destroy ONLY the cyan crown, leave everything else perfect
c=a.copy(); rgb=c[...,:3]
cyan=(rgb[...,2]>150)&(rgb[...,1]>150)&(rgb[...,0]<170)&((rgb[...,2]-rgb[...,0])>40)
c[...,:3][cyan]=[200,120,60]
show(f"cyan crown recoloured orange ({cyan.sum()}px)", Image.fromarray(c.astype(np.uint8),"RGBA"))
print("\nPOSITIVE CONTROLS (should PASS):")
show("unmodified layer", full, expect="PASS")
show("correct hue-safe relight", relight(full,light,spill_color=(40,90,100)), expect="PASS")
print(f"\nincorrect verdicts: {bad}")
