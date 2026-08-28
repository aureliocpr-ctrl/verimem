# -*- coding: utf-8 -*-
"""PERCHE' IL GATE RIFIUTA UN FATTO VERO: il sospetto e le sue alternative.

Alle 19:52 ho misurato che su una fonte reale (`git log --shortstat`) il claim
VERO «il commit X ha aggiunto 86 inserzioni» viene quarantinato con ground 2.8 e
`layers=['L4-grounding', 'L4-negazione', 'L4.2']` — L4-negazione su un claim che
non nega niente. Ho scritto che la causa non ce l'avevo.

Guardando il claim c'e' un sospetto preciso: il subject del commit, che il claim
CITA, e' «docs: dieci variabili che abbiamo nell'ambiente e la...». Contiene
**dieci**, un numero scritto a parole. ⇒ il claim porta due quantita': quella
vera (86) e una che viene dal titolo citato.

Il banco non si ferma al sospetto: prova cinque varianti dello stesso fatto vero,
ognuna che toglie UNA cosa, e guarda quale passa.

  A  claim intero, subject citato per esteso        (la cella gia' misurata)
  B  subject accorciato PRIMA del numero a parole
  C  subject sostituito dall'hash del commit
  D  claim senza il subject: solo «un commit ha aggiunto 86 inserzioni»
  E  claim con il numero a parole ma senza la cifra vera

  se passa B e non A            -> e' il numero a parole nel titolo citato
  se passano C e D              -> e' la citazione del subject, non il numero
  se non passa nessuna          -> il rifiuto non dipende dalla forma del claim
                                   e il sospetto cade

CONTROLLO CHE DEVE POTER FALLIRE: la cifra vera (86) deve stare nella fonte, e
il fatto dev'essere davvero vero — il banco stampa la riga del log che lo
sostiene, cosi' chi legge verifica invece di fidarsi.

    python docs/stato-reale/banchi/perche-il-gate-rifiuta-un-fatto-vero.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    try:
        out = subprocess.run(
            ["git", "log", "--shortstat", "--format=@@%h|%s", "-n", "400"],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: git log — {type(e).__name__}: {e}")
        return 1
    if out.returncode != 0:
        print(f"NON RIUSCITO: git log returncode {out.returncode}")
        return 1

    righe = out.stdout.splitlines()
    log = " ".join(x.strip() for x in righe if x.strip()).replace("@@", "")

    # ricostruisco (hash, subject, inserzioni) e cerco il commit gia' misurato
    voci, corrente = [], None
    for riga in righe:
        r = riga.strip()
        if r.startswith("@@"):
            h, _, s = r[2:].partition("|")
            corrente = (h, s)
        elif "insertion" in r and corrente:
            m = re.search(r"(\d+) insertion", r)
            if m:
                voci.append((corrente[0], corrente[1], m.group(1)))
            corrente = None

    scelti = [v for v in voci if "dieci" in v[1] and len(re.findall(rf"\b{v[2]}\b", log)) == 1]
    if not scelti:
        print("NON RIUSCITO: non trovo il commit con «dieci» nel subject e inserzioni univoche")
        return 1
    h, sog, ins = scelti[0]
    print(f"  commit: {h}  inserzioni {ins}")
    print(f"  subject: {sog[:70]}")
    riga_prova = [x.strip() for x in righe if f"{ins} insertion" in x]
    print(f"  la riga del log che sostiene il fatto: {riga_prova[0] if riga_prova else '???'}")
    if ins not in log:
        print("CONTROLLO CADUTO: la cifra vera non e' nel log")
        return 1
    print("  CONTROLLO retto: la cifra vera e' nel log\n")

    taglio = sog.split("dieci")[0].strip() or sog[:20]
    VARIANTI = {
        "A intero": f"Il commit «{sog}» ha aggiunto {ins} inserzioni.",
        "B tagliato": f"Il commit «{taglio}» ha aggiunto {ins} inserzioni.",
        "C hash": f"Il commit {h} ha aggiunto {ins} inserzioni.",
        "D senza subject": f"Un commit ha aggiunto {ins} inserzioni.",
        "E senza cifra": f"Il commit «{sog}» ha aggiunto alcune inserzioni.",
    }

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "perche.db"))
    fonte = log[:26000]

    import json
    print(f"  {'variante':<18} {'esito':<13} {'ground':>7}   lame")
    print("  " + "-" * 68)
    esiti = {}
    for nome, prop in VARIANTI.items():
        ric = mem.add(prop, topic=f"pq/{nome[0]}", source=fonte, validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        blob = json.dumps(ric.get("warnings"), default=str) + json.dumps(ric.get("moat"), default=str)
        lame = ",".join(x for x in ("L4.1", "L4.2", "L4-grounding", "L4-negazione", "L4-review")
                        if x in blob) or "-"
        esiti[nome] = (st != "quarantined", g, lame)
        print(f"  {nome:<18} {st:<13} {g:7.1f}   {lame}")

    passate = [k for k, (e, _g, _l) in esiti.items() if e]
    print(f"\n  passate: {passate if passate else 'nessuna'}")
    a_ok = esiti["A intero"][0]
    b_ok = esiti["B tagliato"][0]
    c_ok, d_ok = esiti["C hash"][0], esiti["D senza subject"][0]
    print()
    if b_ok and not a_ok:
        print("  => E' IL NUMERO A PAROLE nel titolo citato: togliendo «dieci» dal claim")
        print("     lo stesso fatto vero passa. Il gate conta una quantita' che non e'")
        print("     un'affermazione del claim ma una parola del titolo che cita.")
    elif (c_ok or d_ok) and not a_ok:
        print("  => E' LA CITAZIONE DEL SUBJECT: senza il titolo il fatto vero passa,")
        print("     e non c'entra il numero a parole.")
    elif not passate:
        print("  => NESSUNA variante passa: il rifiuto non dipende dalla forma del claim.")
        print("     Il sospetto cade, e la causa e' altrove.")
    else:
        print("  => quadro misto: guarda le lame riga per riga prima di concludere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
