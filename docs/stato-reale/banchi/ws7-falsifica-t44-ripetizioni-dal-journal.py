"""Falsificazione di T4.4 (@ws5) con un campo diverso: il JOURNAL, non la tabella.

COSA VERIFICO. @ws5 il 02/09 alle 13:25 ha falsificato T4.4 prima di
implementarla: le ripetizioni bit-identiche di chiamata al giudice sono l'1,2%
e non il 15% previsto dal piano, un fattore 12.

  TUTTI i giudicati   7830   95 ripetizioni   1,2%
  QUARANTINATI         763   46               6,0%
  AMMESSI              7067   49              0,7%

E DICHIARA IL PROPRIO LIMITE: la tabella non ha la colonna `source`, quindi ha
usato `grounding_span`, che e' TRONCATO a 400 caratteri. Due source diverse
possono condividere lo stesso span ⇒ il suo 1,2% e' un LIMITE SUPERIORE.

PERCHE' QUESTO BANCO NON RIPETE IL SUO. Una controfirma che rifa' la stessa
query duplica invece di verificare (lezione mia, `LANT-162`). Qui cambio TRE
cose insieme, e ognuna e' dichiarata:
  · SUPERFICIE: il journal `events.jsonl`, non la tabella `facts`
  · CAMPO: `grounding_score` a doppia precisione, non `grounding_span`
  · PERIODO: il journal copre la finestra recente, non lo storico

🔑 E IL BIAS E' OPPOSTO AL SUO, che e' la ragione per cui questo confronto vale.
Lo span troncato SOVRASTIMA le ripetizioni (span uguali, source diverse). Il
punteggio a 15 cifre non puo' sovrastimare: due input diversi che collidono a
quella precisione sono un caso raro. Puo' invece SOTTOSTIMARE, se il giudice
desse punteggi diversi alla stessa coppia (non deterministico).
⇒ Se due proxy con bias opposti danno lo stesso ordine di grandezza, il numero
regge. Se divergono, la differenza dice QUALE dei due bias e' quello vero.

⚠️ CONTROLLO POSITIVO, e non e' inventato: il 02/09 alle 01:58 ho scritto lo
STESSO claim con la STESSA source su due data dir (rami A e B del banco sul
giudice) e ho ottenuto **99.91475677490234 due volte**. Se questo banco non
vede quella coppia, e' cieco e il verdetto e' «non riproducibile» per colpa mia.

⚠️ E la n e' piccola: il journal ha poche centinaia di `flow.write`. L'intervallo
va dichiarato, non nascosto.
"""
import json
import sys
from collections import Counter
from pathlib import Path

JOURNAL = Path.home() / ".engram" / "events.jsonl"
#: il journal ruota: chi legge solo il file corrente misura la coda
ROTAZIONI = [JOURNAL] + [JOURNAL.with_suffix(f".jsonl.{i}") for i in (1, 2, 3)]
# 🔴 02/09 13:40 — IL PRIMO CONTROLLO POSITIVO ERA MAL SCELTO, NON CIECO IL BANCO.
# Avevo messo 99.91475677490234, misurato alle 01:58 dal banco sul giudice. Ma
# quel banco girava con HIPPO_DATA_DIR su una cartella TEMPORANEA, quindi il suo
# journal non e' questo — e il prodotto me lo aveva perfino detto con un
# RuntimeWarning che ho letto e poi dimenticato.
# ⇒ Un controllo positivo deve puntare alla STESSA superficie che si misura.
# Quello valido e indipendente: due righe con lo STESSO fact_id sono la stessa
# scrittura, quindi DEVONO avere lo stesso grounding_score. Se il metodo non le
# vede, non vede nemmeno le ripetizioni vere.

#: topic dei nostri banchi: chiamate di MISURA, non di uso. Vanno separate, o si
#: conta quante volte ci siamo misurati invece di quante volte il prodotto lavora.
TOPIC_DI_PROVA = ("censimento/", "t/x", "vol/", "prova", "banco", "test",
                  "ws1/", "ws2/", "ws3/", "ws4/", "ws5/", "ws6/", "ws7/", "ws8/",
                  "lab/", "smoke", "demo")


def main() -> int:
    righe, letti = [], []
    for p in ROTAZIONI:
        if p.exists():
            righe += p.read_text(encoding="utf-8", errors="replace").splitlines()
            letti.append(f"{p.name} ({p.stat().st_size // 1024} KB)")
    if not righe:
        print(f"  {JOURNAL} non trovato")
        return 2

    scritture = []
    for l in righe:
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("name") == "flow.write":
            pl = d.get("payload", {})
            g = pl.get("grounding_score")
            if g is not None:
                scritture.append((repr(g), pl.get("status"), pl.get("topic"),
                                  pl.get("fact_id")))

    print(f"  file letti: {', '.join(letti)}")
    print(f"  flow.write con grounding_score: {len(scritture)}\n")

    def e_di_prova(t) -> bool:
        return any(k in str(t or "") for k in TOPIC_DI_PROVA)

    def conta(sub, eti: str) -> None:
        c = Counter(g for g, *_ in sub)
        r = sum(n - 1 for n in c.values() if n > 1)
        print(f"  {eti:<26} {len(sub):>5} chiamate  {r:>4} ripetizioni"
              f"  = {100*r/max(1,len(sub)):5.1f}%")

    prova = [s for s in scritture if e_di_prova(s[2])]
    reali = [s for s in scritture if not e_di_prova(s[2])]
    print("  🔑 LE DUE POPOLAZIONI SONO DIVERSE, e mescolarle era il difetto:")
    conta(scritture, "TUTTE le chiamate")
    conta(prova, "topic di PROVA (banchi)")
    conta(reali, "topic REALI")
    print()
    for eti, quar in (("REALI quarantinati", True), ("REALI ammessi", False)):
        conta([s for s in reali if (s[1] == "quarantined") == quar], eti)

    print("\n  --- i cinque valori piu' ripetuti fra i REALI (stampo CHI) ---")
    per_reale = Counter(g for g, *_ in reali)
    for g, n in per_reale.most_common(5):
        if n > 1:
            topic = next((t for gg, _, t, _ in reali if gg == g), "?")
            print(f"     {g:<22} {n}x   topic={str(topic)[:36]}")

    # CONTROLLO POSITIVO: righe con lo STESSO fact_id sono la stessa scrittura e
    # devono avere lo stesso punteggio. Se il metodo non le vede, e' cieco.
    per_fid: dict = {}
    for g, _, _, fid in scritture:
        if fid:
            per_fid.setdefault(fid, set()).add(g)
    doppi = [f for f, gs in per_fid.items() if len(gs) == 1
             and sum(1 for _, _, _, x in scritture if x == f) > 1]
    print(f"\n  CONTROLLO POSITIVO — fact_id ripetuti col MEDESIMO punteggio: "
          f"{len(doppi)}")
    if doppi:
        f = doppi[0]
        print(f"     esempio: {f} compare "
              f"{sum(1 for _, _, _, x in scritture if x == f)} volte, "
              f"un solo valore ⇒ ✅ il metodo VEDE le ripetizioni")
        return 0
    print("     🔴 nessuna: il banco non vede ripetizioni che devono esserci")
    print("     ⇒ verdetto «non riproducibile», e il difetto e' MIO.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
