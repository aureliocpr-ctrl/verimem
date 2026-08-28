"""I 471 QUARANTINATI SENZA GIUDIZIO — il 43,7% della coda, mai indagato.

W7-43 ha misurato che dei **1079 quarantinati vivi** solo **608 (56,3%)** hanno
un `grounding_score`: gli altri **471 (43,7%)** non sono stati giudicati dal
moat. Il dossier ⑮ li dichiara come limite («*non li ho indagati: non so perche'
non abbiano un giudizio*»). Qui li guardo.

TRE IPOTESI, e vanno separate perche' portano a conclusioni opposte:
  (a) **ARCHEOLOGIA** — sono vecchi, di un'era in cui il campo non si popolava.
      ⇒ non e' un difetto vivo, e curarlo sarebbe curare il passato.
  (b) **SENZA FONTE** — scritti senza `source`, quindi il moat non aveva niente
      da confrontare. ⇒ e' il comportamento dichiarato, non un difetto.
  (c) **FERMATI PRIMA** — un layer lessicale li ha bloccati prima che il moat
      girasse. ⇒ e' una scelta di ordine, e si vede da `quarantined_by`.

⚠️ Nessuna delle tre e' un difetto di per se': **il valore di questa misura e'
distinguere quale sia**, perche' il dossier ⑮ le lascia tutte e tre aperte.

CONTROLLI CHE POSSONO FALLIRE:
 (1) le DATE: se i 471 sono tutti anteriori all'era del campo, e' (a) e il resto
     non conta. Confronto la loro distribuzione temporale con quella dei 608.
 (2) DUE denominatori su ogni quota, come sempre.
 (3) se `created_at` non e' leggibile come data, lo dico invece di inventare
     un'era.

    python -u docs/stato-reale/banchi/i-471-senza-giudizio-chi-sono.py
"""

from __future__ import annotations

import collections
import sqlite3
import sys


def main() -> int:
    try:
        from verimem.config import CONFIG
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = list(con.execute(
        "SELECT grounding_score, quarantined_by, created_at, proposition, "
        "grounding_span FROM facts "
        "WHERE status='quarantined' AND superseded_by IS NULL"))
    n = len(righe)
    senza = [r for r in righe if r[0] is None]
    con_p = [r for r in righe if r[0] is not None]
    print(f"  db: {CONFIG.semantic_db}")
    print(f"  quarantinati vivi: {n}   senza punteggio: {len(senza)}"
          f"   giudicati: {len(con_p)}")
    if not senza:
        print("  NON RIUSCITO: nessuno senza punteggio, il banco non ha oggetto.")
        return 1

    print("\n  == (c) CHI LI HA FERMATI — `quarantined_by` sui 471")
    d = collections.Counter((q or "<VUOTA>").strip() or "<VUOTA>"
                            for _s, q, _c, _p, _sp in senza)
    for k, v in d.most_common(8):
        print(f"     {v:>5}  ({100.0 * v / len(senza):>5.1f}% dei 471"
              f" · {100.0 * v / n:>5.1f}% di tutti)  {k}")

    print("\n  == (b) HANNO UNO SPAN? (proxy di «c'era una fonte»)")
    sp_senza = sum(1 for _s, _q, _c, _p, sp in senza if sp)
    sp_con = sum(1 for _s, _q, _c, _p, sp in con_p if sp)
    print(f"     senza punteggio: {sp_senza} su {len(senza)}"
          f"  ({100.0 * sp_senza / len(senza):.1f}%)")
    print(f"     giudicati      : {sp_con} su {len(con_p)}"
          f"  ({100.0 * sp_con / max(1, len(con_p)):.1f}%)")

    print("\n  -- CONTROLLO (3): `created_at` e' leggibile come data?")
    campione = [c for _s, _q, c, _p, _sp in righe[:20] if c]
    if not campione:
        print("     CADUTO - created_at vuoto sul campione: non posso datare")
        print("     niente, e l'ipotesi (a) resta non verificabile da qui.")
        return 1
    print(f"     esempio: {campione[0]!r}")

    # ⚠️ `created_at` e' un TIMESTAMP EPOCH float (es. 1778504164.8468294), non
    # una data ISO. La prima stesura ne prendeva i primi 7 caratteri credendoli
    # «anno-mese»: produceva una tabella di numeri epoch troncati e un confronto
    # `>= "2026-08"` che era SEMPRE falso — cioe' un verdetto «e' archeologia»
    # arrivato da un criterio che non misurava niente. Il controllo (3)
    # stampava l'esempio e non l'avevo letto.
    import datetime as _dt

    def giorno(c):
        try:
            return _dt.datetime.fromtimestamp(float(c)).strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            return "?"

    g_senza = collections.Counter(giorno(c) for _s, _q, c, _p, _sp in senza)
    g_con = collections.Counter(giorno(c) for _s, _q, c, _p, _sp in con_p)
    if g_senza.get("?", 0) + g_con.get("?", 0) > 0.2 * n:
        print("\n  -- CONTROLLO (3): CADUTO — troppe date illeggibili, non dato")
        return 1

    def estremi(cnt):
        v = sorted(k for k in cnt if k != "?")
        return (v[0], v[-1]) if v else ("?", "?")

    s_min, s_max = estremi(g_senza)
    c_min, c_max = estremi(g_con)
    print("\n  == (a) LE DUE ERE — intervallo di date, non la tabella intera")
    print(f"     senza giudizio: dal {s_min} al {s_max}   ({len(senza)} fatti)")
    print(f"     giudicati     : dal {c_min} al {c_max}   ({len(con_p)} fatti)")

    print("\n  -- CONTROLLO (1): e' ARCHEOLOGIA?")
    if s_max < c_min:
        print(f"     SI, E SENZA SOVRAPPOSIZIONE: l'ultimo senza giudizio e' del")
        print(f"     {s_max}, il primo giudicato del {c_min}. ⇒ Due ere")
        print("     NETTE: il campo ha iniziato a popolarsi e da allora TUTTI i")
        print("     quarantinati hanno un punteggio. Non e' un difetto vivo.")
    elif s_min > c_max:
        print("     ROVESCIATO: i senza giudizio sono i PIU' RECENTI. Il campo")
        print("     ha smesso di popolarsi, ed e' un difetto vivo e grave.")
    else:
        sov = sum(v for k, v in g_senza.items() if k != "?" and k >= c_min)
        print(f"     LE DUE ERE SI SOVRAPPONGONO: {sov} senza giudizio su"
              f" {len(senza)} sono dell'era in cui il campo si popolava.")
        print("     ⇒ NON e' solo archeologia, e quei casi vanno guardati.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
