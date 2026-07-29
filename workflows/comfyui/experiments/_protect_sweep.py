import sys; sys.path.insert(0,".")
from pathlib import Path
from PIL import Image
from app.services.compositor import LightContract, erode_alpha, relight, trim_alpha
from app.services.likeness import measure
L=Path("source_material/imported_canon/character_layers")
R=Path("characters/working/repaired_layers")
SCENES={"cool":dict(a=90.0,k=(150,225,235),f=(30,70,80),s=(40,90,100)),
        "warm":dict(a=20.0,k=(255,190,120),f=(70,55,40),s=(120,80,45)),
        "red": dict(a=90.0,k=(230,90,70),f=(60,25,25),s=(110,40,35))}
PROT=[0.70,0.85,0.92,0.96]
res={p:{"pass":0,"tot":0,"min":100.0,"worst":""} for p in PROT}
for lp in sorted(L.glob("*/*.png")):
    rel=lp.relative_to(L).as_posix()
    use=R/rel if (R/rel).is_file() else lp
    im=erode_alpha(trim_alpha(Image.open(use).convert("RGBA")),1)
    for sn,sc in SCENES.items():
        for p in PROT:
            light=LightContract(key_angle_deg=sc["a"],key_color=sc["k"],fill_color=sc["f"],
                key_strength=0.22,fill_strength=0.10,rim_strength=0.10,
                spill_strength=0.14,protect_neutrals=p)
            r=measure(relight(im,light,spill_color=sc["s"]),use,"X")
            d=res[p]; d["tot"]+=1; d["pass"]+= 1 if r.passed else 0
            if r.score<d["min"]: d["min"]=r.score; d["worst"]=f"{rel} {sn}"
print(f"{'protect':>8s} {'pass':>13s} {'rate':>7s} {'min':>7s}  worst")
for p in PROT:
    d=res[p]
    print(f"{p:8.2f} {d['pass']:5d}/{d['tot']:<7d} {d['pass']/d['tot']:6.1%} {d['min']:7.1f}  {d['worst']}")
