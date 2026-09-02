"""Verifica di `W2-11` (@ws2) su tutto lo store invece che su due fatti.

LA CELLA VERIFICATA dice: «chi legge distingue un fatto giudicato da uno mai
giudicato? SI', ma non dal campo che sembra dirlo», con due riserve —
① `status` vale `model_claim` per ENTRAMBI, quindi il campo dal nome piu' ovvio
non distingue; ② nel recall il primo risultato era quello mai giudicato.
E dichiara il proprio limite: **n=1, due fatti, una query**.

PERCHE' QUESTO BANCO. Una controfirma che rifa' la stessa misura DUPLICA invece
di verificare (l'ho imparato stanotte sbagliando: `LANT-162`). Quindi non rifo'
i suoi due fatti: prendo **la stessa domanda su tutto il corpus**, che e' la
popolazione dove la sua riserva ① puo' essere FALSIFICATA — se su decine di
migliaia di fatti `status` separasse i giudicati dai non giudicati, la sua
riserva cadrebbe.

⚠️ QUESTO BANCO NON VERIFICA LA RISERVA ②: il ranking del recall richiede
l'embedder e un processo con i modelli, e con otto istanze sulla stessa macchina
non lo eseguo. Resta aperta, e lo dico invece di lasciarlo intendere.

REGIME: sola lettura del db di produzione (`mode=ro`, chiesto a `CONFIG` e non
all'intuito: alla radice ce n'e' uno vuoto). Zero scritture, zero modelli.
"""
import sqlite3
import sys
from collections import Counter


def main() -> int:
    from verimem.config import CONFIG

    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
    tot = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    righe = con.execute(
        "SELECT status, grounding_score IS NULL, COUNT(*) "
        "FROM facts GROUP BY status, grounding_score IS NULL"
    ).fetchall()

    per_status: dict[str, Counter] = {}
    for st, is_null, n in righe:
        per_status.setdefault(st or "(vuoto)", Counter())[
            "mai giudicato" if is_null else "giudicato"] += n

    print(f"  fatti nello store: {tot}\n")
    print(f"  {'status':<16} {'giudicato':>10} {'mai giudic.':>12} {'discrimina?':>13}")
    for st, c in sorted(per_status.items(), key=lambda kv: -sum(kv[1].values())):
        g, m = c["giudicato"], c["mai giudicato"]
        # uno status DISCRIMINA se sotto quel valore c'e' solo una delle due
        verdetto = "SI'" if (g == 0 or m == 0) else "NO — mescola"
        print(f"  {st:<16} {g:>10} {m:>12} {verdetto:>13}")

    misti = [st for st, c in per_status.items()
             if c["giudicato"] and c["mai giudicato"]]
    quanti = sum(sum(per_status[st].values()) for st in misti)
    print(f"\n  status che MESCOLANO le due popolazioni: {len(misti)} "
          f"({', '.join(misti) or '-'})")
    print(f"  fatti che stanno sotto uno status che mescola: {quanti}"
          f"  = {100*quanti/max(1,tot):.1f}% del corpus")

    # CONTROLLO POSITIVO: il campo che @ws2 indica come buono DEVE separare.
    nulli = con.execute(
        "SELECT COUNT(*) FROM facts WHERE grounding_score IS NULL").fetchone()[0]
    senza_firma = con.execute(
        "SELECT COUNT(*) FROM facts WHERE grounding_score IS NULL "
        "AND (source_signature IS NULL OR source_signature = '')").fetchone()[0]
    print(f"\n  --- controllo positivo: il campo che la cella indica come buono ---")
    print(f"  mai giudicati (grounding_score NULL)          {nulli}")
    print(f"  di questi, anche senza source_signature       {senza_firma}"
          f"  = {100*senza_firma/max(1,nulli):.1f}%")
    print("  (se questa percentuale fosse bassa, i due campi non andrebbero")
    print("   d'accordo e sarebbe il MIO righello a dover essere spiegato)")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
