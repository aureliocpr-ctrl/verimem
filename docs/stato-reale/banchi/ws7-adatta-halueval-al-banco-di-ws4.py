"""Adattatore: HaluEval heldout nello schema che il banco di @ws4 sa leggere.

PERCHE'. @ws4 ha chiuso l'anello ① di M1: la baseline REGGE IDENTICA dopo 42
commit — veri fermati 88/300 = 29,3%, falsi fermati 260/300 = 86,7%, tabella per
strato invariata cifra per cifra, controllo positivo acceso.
Regime completo e riproducibile ⇒ ammissibile per la falsificazione.

IL CAMPO DIVERSO: un ALTRO CORPUS. Il suo banco gira su
`truthfulqa_pairs_heldout.jsonl`; io gli do `halueval_qa_heldout.jsonl`.
🔑 E NON TOCCO IL SUO BANCO: cambio SOLO la costante del file dati, su una copia
temporanea fuori dal repo. Il codice di misura resta il suo, riga per riga, cosi'
la sola variabile e' il corpus.

LA CONVERSIONE, e le scelte che comporta — dichiarate, non nascoste:
  HaluEval    knowledge / question / right_answer / hallucinated_answer
  serve       claim / source / label
  ⇒ source = knowledge (il passaggio di testo, come in TruthfulQA)
    label 1 = right_answer          label 0 = hallucinated_answer
⚠️ UNA SCELTA C'E' ED E' MIA: in HaluEval le risposte sono SECCHE («Tizio»),
mentre i claim di TruthfulQA sono FRASI AFFERMATIVE. Un claim secco non e' la
stessa cosa di una proposizione. Per ridurre la differenza compongo
`question + " " + answer`, che avvicina la forma a quella di TruthfulQA.
⇒ Questa e' l'unica cosa che aggiungo, e se il risultato divergesse molto
andrebbe controllata rifacendo con la risposta secca.

⚠️ DISCIPLINA DEGLI SPLIT, dal README del progetto: «heldout is RUN, never
read». Ho letto le CHIAVI dello schema, non il contenuto, e questo adattatore
non stampa nessun testo del dataset.

═══ PREDIZIONE, scritta PRIMA di eseguire ═══
P1 falsi fermati >= 86,7%. HaluEval e' costruito con allucinazioni marcate:
   dovrebbero essere piu' facili da fermare che le falsita' di TruthfulQA.
P2 veri persi FRA IL 15% E IL 35%, cioe' lo stesso ordine del 29,3%.
🔑 P2 E' LA PREDIZIONE CHE CONTA: se i veri persi su un altro corpus cadessero
   fuori da quella banda — sotto il 10% o sopra il 50% — allora il 29,3% NON
   sarebbe una proprieta' del gate ma di TruthfulQA, e il muro M1 andrebbe
   ridefinito su quale dataset lo si misura.
P3 il controllo positivo deve accendersi: se i falsi fermati fossero ~0, il
   giudice non ha girato e il verdetto e' «non riproducibile» (W7-87).
"""
import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
SORGENTE = RADICE / "benchmark" / "data" / "external" / "halueval_qa_heldout.jsonl"


def main() -> int:
    if len(sys.argv) < 2:
        print("  uso: ws7-adatta-halueval-al-banco-di-ws4.py <file di uscita>")
        return 2
    uscita = Path(sys.argv[1])
    if not SORGENTE.exists():
        print(f"  {SORGENTE} non trovato")
        return 2

    fuori, saltate = [], 0
    for riga in SORGENTE.read_text(encoding="utf-8").splitlines():
        if not riga.strip():
            continue
        d = json.loads(riga)
        k, q = d.get("knowledge"), d.get("question")
        vero, falso = d.get("right_answer"), d.get("hallucinated_answer")
        if not (k and q and vero and falso):
            saltate += 1
            continue
        fuori.append({"claim": f"{q} {vero}", "source": k, "label": 1,
                      "kind": "halueval", "category": "qa"})
        fuori.append({"claim": f"{q} {falso}", "source": k, "label": 0,
                      "kind": "halueval", "category": "qa"})

    uscita.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in fuori),
                      encoding="utf-8")
    veri = sum(1 for x in fuori if x["label"] == 1)
    print(f"  scritti {len(fuori)} casi in {uscita}")
    print(f"  VERI {veri}   FALSI {len(fuori) - veri}   righe saltate {saltate}")
    # controllo positivo dell'adattatore: le due popolazioni devono essere pari
    # e non vuote, altrimenti la conversione ha perso qualcosa in silenzio
    if veri == 0 or veri != len(fuori) - veri:
        print("  🔴 le due popolazioni non sono pari: conversione difettosa")
        return 1
    print("  ✅ popolazioni pari e non vuote")
    return 0


if __name__ == "__main__":
    sys.exit(main())
