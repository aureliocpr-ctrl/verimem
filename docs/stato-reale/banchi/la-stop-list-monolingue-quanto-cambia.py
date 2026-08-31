"""LA STOP-LIST MONOLINGUE: QUANTI SEGNALI CAMBIANO SE LA CURO.

\U0001f4cc **REPERTO MIO DI IERI SERA (`W7-85`), lasciato libero e non curato.**
`outcome_pattern.py`, `failure_clusters.py` e `failure_diagnosis.py` hanno una
stop-list con **11 voci EN e 0 IT**, e alla porta del tool MCP
`hippo_outcome_patterns` escono **«per» (41), «con» (37), «non» (25)** fra i
*«tokens correlated with success»*.

⚠️ **Allora avevo scritto**: *«non lo curo perche' cambierebbe QUALI token
escono ⇒ serve una misura appaiata e un voto separato»*. **Questa e' la
misura**, e viene prima della proposta.

\U0001f511 **LE VOCI VENGONO DAL CORPUS, NON DALL'INTUITO** — e' la lezione di
`W7-84`, dove la stessa forma di difetto (`_GRAMMATICA` monolingue) l'avevo
curata prendendo i token **dalla classifica dei casi reali**. Qui idem: guardo
quali parole funzionali italiane **passano davvero** la `_STOP` e finiscono fra
i segnali.

\U0001f6a8 **E GLI AMBIGUI RESTANO FUORI**: in italiano «danno», «conta»,
«stato», «era», «sono» (nome proprio no, ma «i suoi») possono essere
**sostantivi**. Una parola che puo' nominare qualcosa non entra in una lista di
non-parole, per quanto frequente sia come funzione.

ATTESA DICHIARATA PRIMA: **cambieranno pochi segnali, meno di dieci**, ma
**saranno quelli in cima** — perche' le parole funzionali sono le piu'
frequenti e la classifica e' ordinata per frequenza. ⚠️ **Se non cambiasse
nulla, la cura non serve e lo dico.** ⚠️ **Se cambiasse mezza classifica, la
cura e' piu' invasiva di quanto pensassi e va discussa prima.**

CONTROLLI CHE POSSONO FALLIRE:
 (1) ✅ **la classifica NON deve svuotarsi**: se dopo la cura restassero
     pochissimi segnali, sto togliendo troppo.
 (2) 🪞 **stampo i token TOLTI e quelli NUOVI**, non solo il conteggio: la
     lista va contestata voce per voce.
 (3) ⚖️ **la funzione e' PURA e il confronto e' A/B nella stessa esecuzione**,
     quindi immune al corpus che si muove.
 (4) 🔴 **non tocco il codice**: passo la lista curata come parametro locale,
     cosi' il banco misura la cura **senza applicarla**.

    python -u docs/stato-reale/banchi/la-stop-list-monolingue-quanto-cambia.py
"""

from __future__ import annotations

import sqlite3
import sys
from types import SimpleNamespace

#: (2) i candidati: parole funzionali IT che NON sono anche sostantivi.
#: Ambigui tenuti fuori di proposito: danno, conta, stato, era, torno, parte.
CANDIDATI = {
    "per", "con", "non", "che", "come", "sul", "sulla", "nel", "nella",
    "dei", "delle", "degli", "dal", "dalla", "alla", "allo", "agli",
    "una", "uno", "gli", "questo", "questa", "quello", "quella",
    "piu", "meno", "anche", "solo", "ancora", "poi", "quando", "dove",
    "sono", "hanno", "essere", "avere", "fare", "dire",
}
AMBIGUI = {"danno", "conta", "stato", "era", "parte", "torno", "fine",
           "modo", "caso", "punto", "campo", "resto"}


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.outcome_pattern import _STOP, _TOKEN_RE, find_outcome_patterns
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print(f"  `_STOP` attuale: {len(_STOP)} voci")
    print(f"  di cui italiane: "
          f"{len(_STOP & (CANDIDATI | AMBIGUI))}   <- il difetto di `W7-85`")

    db = str(CONFIG.semantic_db).replace("semantic\\semantic.db",
                                         "episodes\\episodes.db")
    try:
        con = sqlite3.connect(db)
        eps = [SimpleNamespace(task_text=t or "", outcome=o or "")
               for t, o in con.execute(
                   "select task_text, outcome from episodes "
                   "where task_text is not null")]
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: episodi illeggibili da {db} - {e}")
        return 1
    print(f"  episodi con task_text: {len(eps)}")
    if len(eps) < 50:
        print("NON RIUSCITO: meno di cinquanta episodi.")
        return 1

    # (3) A/B nella stessa esecuzione, (4) senza toccare il codice
    prima = find_outcome_patterns(eps, min_occurrence=3)
    tok_prima = [s["token"] for s in prima.get("positive_signals", [])]

    # la cura simulata: rifaccio il conteggio con la lista estesa
    esteso = set(_STOP) | CANDIDATI
    occ: dict[str, int] = {}
    succ: dict[str, int] = {}
    for ep in eps:
        parole = {t.lower() for t in _TOKEN_RE.findall(ep.task_text or "")
                  if t.lower() not in esteso and len(t) > 2}
        for t in parole:
            occ[t] = occ.get(t, 0) + 1
            if ep.outcome == "success":
                succ[t] = succ.get(t, 0) + 1
    dopo = [(t, n, succ.get(t, 0) / n) for t, n in occ.items() if n >= 3]
    dopo = [d for d in dopo if d[2] >= 0.7]
    dopo.sort(key=lambda d: (-d[2], -d[1]))
    tok_dopo = [d[0] for d in dopo[:30]]

    # (1) il controllo che deve poter fallire
    if len(tok_dopo) < 5:
        print(f"\n     CADUTO (controllo 1): dopo la cura restano"
              f" {len(tok_dopo)} segnali.")
        print("     Sto togliendo troppo: la cura non e' proponibile cosi'.")
        return 1

    tolti = [t for t in tok_prima if t not in tok_dopo]
    nuovi = [t for t in tok_dopo if t not in tok_prima]
    print(f"\n  == L'A/B, stessa esecuzione, {len(eps)} episodi")
    print(f"     segnali PRIMA : {len(tok_prima)}")
    print(f"     segnali DOPO  : {len(tok_dopo)}")
    print(f"     TOLTI  ({len(tolti)}): {tolti}")
    print(f"     NUOVI  ({len(nuovi)}): {nuovi}")

    print("\n  -- (2) la classifica PRIMA (i primi 12)")
    for s in prima.get("positive_signals", [])[:12]:
        seg = "🔴" if s["token"] in CANDIDATI else "  "
        print(f"     {seg} {s['token']:<18}{s['n_occurrences']:>5}")
    print("\n  -- la classifica DOPO (i primi 12)")
    for t, n, _r in dopo[:12]:
        print(f"        {t:<18}{n:>5}")

    print("\n  == LA RIGA CHE CONTA")
    funz = [t for t in tolti if t in CANDIDATI]
    if not tolti:
        print("     🟢 **NESSUN SEGNALE CAMBIA**: la cura non serve su questo")
        print("     corpus, e lo dico con la stessa forza con cui l'avrei")
        print("     proposta.")
    elif len(tolti) <= 10:
        print(f"     🟡 **{len(tolti)} segnali cambiano**, di cui **{len(funz)}"
              " sono parole")
        print(f"     funzionali italiane**: {funz}")
        print("     ⇒ **La cura e' piccola e mirata**: toglie rumore dalla"
              " cima della")
        print("     classifica senza rifarla. E' proponibile al voto.")
    else:
        print(f"     🔴 **{len(tolti)} segnali cambiano**: la cura e' piu'")
        print("     INVASIVA di quanto pensassi e **non la propongo cosi'** —")
        print("     va discussa prima, perche' rifa' la classifica invece di")
        print("     ripulirla.")

    print("\n  ⚠️ COSA NON DICE: la lista dei candidati e' **mia** e va"
          " contestata")
    print("  voce per voce · gli AMBIGUI sono tenuti fuori di proposito"
          " (`danno`,")
    print("  `conta`, `stato`, `era`…) · e questo misura **`outcome_pattern`**:")
    print("  `failure_clusters` e `failure_diagnosis` hanno la stessa lista ma")
    print("  un'altra funzione, e vanno misurati a parte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
