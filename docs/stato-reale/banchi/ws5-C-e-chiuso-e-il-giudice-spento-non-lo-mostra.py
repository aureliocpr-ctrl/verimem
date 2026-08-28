# -*- coding: utf-8 -*-
r"""Il difetto [C] E' CHIUSO - e col giudice SPENTO non lo si sarebbe mai visto.

Paga il debito piu' vecchio che avevo: il 28/08 avevo documentato [C] («*un
claim SENZA source ritira un fatto VERIFICATO*», referto `07ce9cad5e2b42bf`,
riprodotto col giudice acceso: vero a 98.38 `moat=passed`, ritirato da un claim
`moat=not_run:no_source`) e avevo dichiarato non fatto il caso col **giudice
spento**. Eseguito adesso, nei DUE regimi, stesso banco (del 20/08, immutato),
stesso SHA `e6ebabd8`::

    A) GIUDICE SPENTO (`ENGRAM_LOCAL_GATE_MODEL` -> cartella vuota)
       giudice disponibile: False
       A confab (no source)  VERO grounding=None moat=not_run:no_judge  superseded_by=None
       B aggior (con source) VERO grounding=None moat=not_run:no_judge  superseded_by=None

    B) GIUDICE ACCESO
       giudice disponibile: True
       A confab (no source)  VERO grounding=98.38 moat=passed  superseded_by=None
                             NUOVO **quarantined**, warning L3
       B aggior (con source) VERO superseduto da 6c7d87dfe2a1  (comportamento GIUSTO)

⇒ 🟢 **[C] NON SI RIPRODUCE PIU'.** Col giudice acceso il claim senza source
viene **quarantinato** e il fatto vero **resta**.
🪞🔴 **RITIRO: LA CURA E' DEL 21/08 E IL MIO REFERTO DEL 28/08 ERA SBAGLIATO.**
Avevo scritto qui che la cura era di @ws6 (`956844f4`, 28/08 23:23) e che
`aeee8305` del 21/08 «non bastava». **Falso su entrambi i punti**, e l'ho
scoperto facendo l'A/B che avevo dichiarato non fatto - in un **worktree
separato**, senza toccare l'albero condiviso::

    42bb3839  (20/08 18:56, PRIMA di `aeee8305`)
        A confab (no source)  VERO **superseded_by=a1acc92c91ce**   <== IL DIFETTO C'E'
    b5af2ba0  (`956844f4^`, ieri sera, PRIMA della cura di @ws6)
        A confab (no source)  VERO superseded_by=None, NUOVO quarantined   <== GIA' CURATO
    HEAD (oggi)
        identico a b5af2ba0

⇒ **La cura e' `aeee8305`** (21/08 10:02, «*una scrittura senza source non
supersede un fatto groundato*»), che porta con se' anche la guardia
`tests/test_guardia_C_senza_source_non_supersede.py`. La cura di @ws6 su
`_route_evolutions` e' un'altra cosa e **non c'entra con [C]**: l'avevo
attribuita a lei per aver seguito `git log -S` fino al commit piu' RECENTE
invece di al piu' VECCHIO.
⇒ 🔴 **E QUINDI IL MIO REFERTO DEL 28/08 (`07ce9cad5e2b42bf`) ERA FALSO**: dicevo
di aver riprodotto [C] col giudice acceso, ma quel giorno la cura c'era da una
settimana **e con un presidio**. Non so con certezza cosa misurai; l'ipotesi
piu' probabile e' che l'albero fosse vecchio - quel giorno mi era gia'
successo di lavorare **21 commit indietro** e di trarne una conclusione
sbagliata.
🔑 **La lezione: «un rosso che non si riproduce» ha una TERZA lettura** oltre a
«instabile» e «curato dopo» - **«non era mai stato vero»**. E si distinguono
solo con l'A/B sul commit, che e' precisamente il debito che avevo dichiarato
e stavo per lasciare aperto.

🔑 **E IL REGIME SPENTO NON AVREBBE MOSTRATO NIENTE**, che e' il motivo per cui
valeva la pena pagarlo: senza giudice il primo fatto **non e' mai «verificato»**
(`moat=not_run:no_judge`), quindi **sparisce la premessa stessa del difetto**.
⇒ Un banco che gira col giudice spento su questa classe **non produce un rosso
ne' un verde: produce un'assenza di misura** - ed e' la trappola che abbiamo
gia' in memoria («*una misura che non c'e' si legge come una misura perfetta*»).

⚖️ PUNTI DEBOLI: **non ho isolato con un A/B quale dei 283 commit chiude il
caso** - ho seguito `git log -S cand_ha_source` fino a due commit, non ho
rimosso la cura per vedere il rosso tornare. E il banco e' **un solo caso** per
regime.

REGIME: SHA `e6ebabd8` letto nella stessa esecuzione · store temporaneo
`HIPPO_DATA_DIR` da `trap` · due processi separati, unica variabile
`ENGRAM_LOCAL_GATE_MODEL`.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-C-e-chiuso-e-il-giudice-spento-non-lo-mostra.py
            e con ENGRAM_LOCAL_GATE_MODEL puntato a una cartella vuota per il regime A.
"""
import tempfile
from pathlib import Path
from verimem.local_grounding import local_ce_available
from verimem.client import Memory

VERO = "The payment service uses port 8080."
CASI = [
    ("A confab (no source)", "The payment service uses port 9999.", None),
    ("B aggior (con source)", "The payment service uses port 8081.",
     "The payment service uses port 8081."),
]
print("giudice disponibile: %s" % local_ce_available())
for et, nuovo, src_nuovo in CASI:
    tmp = Path(tempfile.mkdtemp(prefix="ws5_C2_"))
    m = Memory(path=tmp / "d.db")
    r1 = m.add(VERO, topic="c/pay", source=VERO, verified_by=["source-doc:acme:1"], validate="full")
    kw = {"topic": "c/pay", "verified_by": ["source-doc:acme:1"], "validate": "full"}
    if src_nuovo:
        kw["source"] = src_nuovo
    r2 = m.add(nuovo, **kw)
    f1 = m.semantic.get(r1["id"])
    print("--- %s" % et)
    print("    VERO   id=%s grounding=%s moat=%s status=%s superseded_by=%s" % (
        r1.get("id"), r1.get("grounding_score"), r1.get("moat"), r1.get("status"),
        getattr(f1, "superseded_by", None)))
    print("    NUOVO  id=%s grounding=%s moat=%s status=%s superseded=%s" % (
        r2.get("id"), r2.get("grounding_score"), r2.get("moat"), r2.get("status"),
        r2.get("superseded")))
    for w in (r2.get("warnings") or []):
        print("       warning: %s | %s" % (w.get("layer"), str(w.get("advice"))[:70]))
