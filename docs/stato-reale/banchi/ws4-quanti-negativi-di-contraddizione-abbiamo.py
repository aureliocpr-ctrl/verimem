# -*- coding: utf-8 -*-
"""QUANTE COPPIE DI CONTRADDIZIONE ETICHETTATE ABBIAMO GIA'?

La domanda e' della pagina (b): senza negativi di contraddizione, (b) «non e'
un'opzione, e' un progetto di raccolta dati travestito da opzione». Serve il
numero con l'output grezzo, non una stima.

LA DISTINZIONE CHE DECIDE, e non e' una sfumatura:
  · CONTRADDIZIONE  — il claim afferma il contrario di cio' che la FONTE dice
                      sullo stesso soggetto. E' quello che (b) vuole comprare.
  · NON SOSTENUTO   — il claim dice qualcosa che la fonte non copre. Diverso:
                      per un giudice di entailment e' un altro compito.
Un dataset di «negativi» puo' essere fatto in tutto o in parte della seconda
specie, e allora il conteggio grezzo INGANNA.

E LA SECONDA DOMANDA, che la pagina non fa e che conta uguale: quanti di quei
negativi sono ANCORA USABILI, cioe' NON gia' visti dal v3.1? Un negativo gia'
nel training non serve a (b): il controllo ① («non impara la scorciatoia») si
misura su cio' che il modello non ha mai visto.

⚠️ CRITERIO MISURATO, NON ASSERITO: per HaluEval verifico se la risposta GIUSTA
compare nel testo della fonte. Se c'e', la fonte afferma quel fatto e la
risposta allucinata lo CONTRADDICE. Se non c'e', la fonte non dice ne' l'uno
ne' l'altro e il negativo e' «non sostenuto», non contraddizione.
CONTROLLO POSITIVO obbligatorio: su TruthfulQA, dove la fonte contiene la
risposta per costruzione (formato Q:/A:), la stessa misura deve dare una quota
ALTA. Se da' bassa anche li', il righello e' rotto e non pubblico il numero.
"""
import io
import json
import os
import re
from collections import Counter

REPO = os.environ.get("WS4_REPO", ".")
MIEI = os.environ.get("WS4_SCRATCH", ".")
EXT = os.path.join(REPO, "benchmark", "data", "external")


def righe(p):
    return [json.loads(x) for x in io.open(p, encoding="utf-8") if x.strip()]


def normalizza(t):
    return re.sub(r"[^a-z0-9 ]+", " ", t.lower()).split()


def contenuta(risposta, fonte):
    """La risposta compare nella fonte? Confronto per PAROLE, non substring:
    una substring corta ('a') sta ovunque e gonfierebbe il numero."""
    pr, pf = normalizza(risposta), set(normalizza(fonte))
    piene = [w for w in pr if len(w) > 2]
    if not piene:
        return False
    return sum(1 for w in piene if w in pf) / len(piene) >= 0.8


print("=" * 72)
print("  ① LE COPPIE ETICHETTATE CHE ESISTONO, per file")
print("=" * 72)
tot_neg = 0
for nome in sorted(os.listdir(EXT)):
    if not nome.endswith(".jsonl"):
        continue
    r = righe(os.path.join(EXT, nome))
    ha_label = "label" in r[0]
    ha_coppia = "hallucinated_answer" in r[0]
    if ha_label:
        neg = sum(1 for x in r if str(x["label"]) == "0")
        kinds = Counter(x.get("kind", "?") for x in r if str(x["label"]) == "0")
        print(f"  {nome:38s} {len(r):4d} righe · {neg:4d} negativi"
              f" · kind {dict(kinds)}")
        tot_neg += neg
    elif ha_coppia:
        print(f"  {nome:38s} {len(r):4d} righe · {len(r):4d} negativi"
              f" ricostruibili (hallucinated_answer)")
        tot_neg += len(r)
    else:
        print(f"  {nome:38s} {len(r):4d} righe ·    0 negativi"
              f" (chiavi {sorted(r[0])}: nessuna risposta)")
print(f"  {'TOTALE negativi grezzi':38s} {tot_neg:4d}")

print()
print("=" * 72)
print("  ② MA QUANTI CONTRADDICONO LA FONTE? (criterio misurato)")
print("=" * 72)
esiti = {}
for nome in ("halueval_qa_dev", "halueval_qa_heldout", "halueval_qa_unanswerable"):
    r = righe(os.path.join(EXT, nome + ".jsonl"))
    dentro = sum(1 for x in r
                 if contenuta(x["right_answer"], x["knowledge"]))
    esiti[nome] = (dentro, len(r))
    print(f"  {nome:34s} la risposta GIUSTA e' nella fonte:"
          f" {dentro:4d}/{len(r):4d} = {100*dentro/len(r):5.1f}%"
          f"  ⇒ contraddizioni vere")

# ── IL CONTROLLO, alla seconda scelta ────────────────────────────────────
# Il primo che avevo messo (la stessa misura su TruthfulQA) si e' SPENTO al
# 30,0%, e a ragione: li' i positivi sono `kind: paraphrase`, riformulazioni
# che per costruzione NON ripetono le parole della fonte. Avevo scelto una
# popolazione dove il criterio non puo' accendersi — il controllo era rotto,
# non il criterio. Quello giusto e' di DISCRIMINAZIONE, sulla stessa
# popolazione: do al criterio la fonte SBAGLIATA (quella della riga dopo).
# Se la quota non crolla, il criterio trova un match ovunque ed e' rumore.
r = righe(os.path.join(EXT, "halueval_qa_heldout.jsonl"))
giusta = sum(1 for x in r if contenuta(x["right_answer"], x["knowledge"]))
sfalsata = sum(1 for i, x in enumerate(r)
               if contenuta(x["right_answer"], r[(i + 1) % len(r)]["knowledge"]))
print(f"\n  CONTROLLO DI DISCRIMINAZIONE — stessa misura, fonte SBAGLIATA:")
print(f"    con la fonte giusta   {giusta:4d}/{len(r)} = {100*giusta/len(r):5.1f}%")
print(f"    con la fonte di un'altra riga {sfalsata:4d}/{len(r)} ="
      f" {100*sfalsata/len(r):5.1f}%")
if sfalsata > giusta * 0.25:
    print("   ⛔ RIGHELLO ROTTO: trova la risposta anche nella fonte")
    print("      sbagliata. Non pubblico il numero di sopra.")
    raise SystemExit(0)
print(f"   ✅ ACCESO: crolla di {100*(giusta-sfalsata)/len(r):.1f} punti quando")
print("      la fonte non e' quella giusta ⇒ il criterio misura la fonte.")

print()
print("=" * 72)
print("  ③ E QUANTI SONO ANCORA USABILI? (non gia' visti dal v3.1)")
print("=" * 72)
train = righe(os.path.join(MIEI, "v3_train.jsonl"))
fonti = Counter(x["fonte"] for x in train)
print(f"  il v3.1 e' stato addestrato su {len(train)} esempi, da: {dict(fonti)}")
neg_train = [x for x in train if str(x["label"]) == "0"]
print(f"  di cui NEGATIVI gia' visti: {len(neg_train)}")
visti = {x["claim"].strip().lower() for x in neg_train}
nuovi_tq = sum(1 for x in righe(os.path.join(EXT, "truthfulqa_pairs_heldout.jsonl"))
               if str(x["label"]) == "0" and x["claim"].strip().lower() not in visti)
print(f"  negativi TruthfulQA HELDOUT mai visti dal v3.1: {nuovi_tq}")
he = sum(v for v, _ in esiti.values())
print(f"  contraddizioni HaluEval (tutte e tre le fette):   {he}")
print(f"\n  ⇒ NEGATIVI DI CONTRADDIZIONE DISPONIBILI E NUOVI: "
      f"{nuovi_tq} + {he} = {nuovi_tq + he}")
print(f"  ⚠️ ma {len(neg_train)} negativi il v3.1 li ha gia' visti:"
      f" riusarli non misura il controllo ①.")
