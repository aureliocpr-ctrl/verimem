"""LIVELLO: gli SCORER, non la porta — si confrontano quattro giudici, non il gate.

Tre modelli candidati contro il nostro, su 30 falsi + 30 veri in italiano.

    python docs/stato-reale/banchi/ws3-P1-tre-modelli-sui-trenta-piu-trenta-italiani.py

⚠️ Carica quattro scorer. Serve uno slot di inferenza. Tutti in cache
(verificato prima di eseguire: `~/.cache/huggingface/hub`, MiniCheck 3,3 GB).

━━ LA DOMANDA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
«Quale modello per il giudice?» — e la risposta va data su un banco ITALIANO,
perche' il corpus vivo e' al 75,8% italiano e i candidati sono NLI inglesi.

    R  il nostro giudice di oggi (CE locale)   <- RIFERIMENTO, non candidato
    A  cross-encoder/nli-deberta-v3-base
    B  MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli
    C  lytang/MiniCheck-DeBERTa-v3-Large

━━ PERCHE' A PARI VERI PERSI, e non a soglia fissa ━━━━━━━━━━━━━━━━━━━━━━━━━━
Le quattro scale non sono confrontabili: il CE locale esce in 0-100 con una
sigmoide sua, i due NLI danno una probabilita' di entailment, MiniCheck un'altra
cosa ancora. A soglia fissa si confronterebbe DOVE OGNUNO HA MESSO IL TAGLIO,
non quanto discrimina. Percio': per ogni quota di veri persi si guarda quanti
falsi vengono fermati, piu' l'AUROC, che e' l'unico numero direttamente
confrontabile fra scale diverse.

━━ PREDIZIONE ws3-P1, depositata sul canale PRIMA di eseguire ━━━━━━━━━━━━━━━
 ① R ha AUROC >= di A e di B, con margine >= 0,05 su almeno uno.
    🔴 muore se A o B supera R di >= 0,05.
 ② C (MiniCheck) sta SOTTO R su questo set italiano.
    🔴 muore se C >= R.
 ③ a pari veri persi del 10%, nessuno ferma piu' di 27/30 falsi — il banco deve
    discriminare, non saturare.
    🔴 muore se qualcuno fa >= 28/30: allora il banco e' troppo facile e i
    confronti di oggi non decidono niente.

━━ PREDIZIONE ws3-P2, depositata prima della seconda condizione ━━━━━━━━━━━━━
 ① B e C perdono < 0,05 di AUROC con la zavorra; R ne perde >= 0,05.
 ② almeno uno fra B e C resta >= 0,95 con la zavorra.
    🔴 muore se crollano entrambi: allora la zavorra non e' un difetto NOSTRO,
    e' un attacco a tutta la famiglia NLI e cambiare modello non cura niente.

━━ MISURATO IL 2026-09-03 alle 21:29 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    FONTE CORTA                  AUROC    falsi fermati:  5%  10%  20%  30%
      R nostro giudice          0.8700                    21   21   24   26
      A nli-deberta-v3-base     0.8633                    20   20   21   27
      B deberta-large-mnli-fever 1.0000                   30   30   30   30
      C MiniCheck-DeBERTa-large  1.0000                   30   30   30   30

    FONTE + FRASE ESTRANEA       AUROC    falsi fermati:  5%  10%  20%  30%
      R nostro giudice          0.8067                    12   17   24   25
      A nli-deberta-v3-base     0.8522                    20   21   21   27
      B deberta-large-mnli-fever 1.0000                   30   30   30   30
      C MiniCheck-DeBERTa-large  1.0000                   30   30   30   30

    quanto costa la frase estranea:
      R  0.8700 -> 0.8067  (-0.0633)   🔴 perde
      A  0.8633 -> 0.8522  (-0.0111)   regge
      B  1.0000 -> 1.0000  (+0.0000)   regge
      C  1.0000 -> 1.0000  (+0.0000)   regge

P1 ①②③ TUTTE E TRE FALSIFICATE (B e C a 1,0000, e 30/30 al 10%).
P2 ① e ② CONFERMATE.

⇒ IL REPERTO, e non e' una classifica: **la frase estranea e' un difetto del
NOSTRO giudice, non della famiglia NLI.** Tre scorer su tre non ne risentono;
il nostro perde 0,0633 di AUROC e, al punto di lavoro del 5% di veri persi,
passa da 21 a 12 falsi fermati — **nove falsi in piu' che entrano per una frase
sulla mensa aziendale.**

⚠️ E IL BANCO RESTA SATURO PER ORDINARE B E C: 1,0000 in ENTRAMBE le condizioni
non permette di dire quale sia migliore. Questo banco risponde a «di chi e' il
difetto», non a «quale modello scegliere». Chi lo usa per la seconda domanda
usa uno strumento che, misurato, non la puo' decidere.

━━ CIO' CHE QUESTO BANCO NON DECIDE, dichiarato prima dei numeri ━━━━━━━━━━━━
Sessanta frasi generate da una tabella di opposizione mia, tutte italiane,
tutte nella stessa forma sintattica, e una sola zavorra sempre uguale. E' un
banco di CONTRADDIZIONE DIRETTA in italiano: non dice niente sulle
contraddizioni IMPLICITE — che sono il caso dove il nostro gate fallisce
davvero — ne' sull'inglese, ne' sui casi lunghi, ne' sul costo in RAM e in
secondi di B e C. Chi legge il vincitore come «il modello migliore» legge piu'
di quanto c'e' scritto.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

QUI = Path(__file__).resolve().parent
QUOTE = [0.05, 0.10, 0.20, 0.30]

MODELLI = {
    "A nli-deberta-v3-base": "cross-encoder/nli-deberta-v3-base",
    "B deberta-large-mnli-fever": "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
    "C MiniCheck-DeBERTa-large": "lytang/MiniCheck-DeBERTa-v3-Large",
}


def casi() -> list[tuple[str, str, str]]:
    """I 30 casi del banco gemello: (fonte, claim FALSO, claim VERO)."""
    s = importlib.util.spec_from_file_location(
        "_trenta", QUI / "ws3-trenta-coppie-con-e-senza-frase-estranea.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m.coppie()


def auroc(pos: list[float], neg: list[float]) -> float:
    """P(punteggio di un VERO > punteggio di un FALSO). Mann-Whitney, pari 0,5."""
    if not pos or not neg:
        return float("nan")
    vinte = sum((1.0 if p > n else 0.5 if p == n else 0.0)
                for p in pos for n in neg)
    return vinte / (len(pos) * len(neg))


def falsi_fermati(veri: list[float], falsi: list[float], quota: float) -> int:
    """Quanti FALSI stanno sotto la soglia che perde `quota` dei VERI.

    ⚠️ Il taglio si prende sui VERI ordinati: e' la definizione di «a pari veri
    persi». Prenderlo sui falsi darebbe un numero che sembra lo stesso e non lo e'.
    """
    ordinati = sorted(veri)
    i = min(len(ordinati) - 1, max(0, int(round(quota * len(ordinati)))))
    taglio = ordinati[i]
    return sum(1 for f in falsi if f < taglio)


def punteggi_nostro(dati) -> tuple[list[float], list[float]]:
    """⚠️ `try_local_score` torna `(punteggio, soglia)` oppure `None`, non un
    numero: si legge `r[0]` come fa il prodotto in `grounding_gate.py:457`.
    Passarlo a `float()` cosi' com'e' solleva TypeError — la prima esecuzione di
    questo banco e' morta li'.
    """
    from verimem.local_grounding import try_local_score

    def uno(fonte: str, claim: str) -> float:
        r = try_local_score(fonte, claim)
        return float(r[0]) if r is not None else 0.0

    veri, falsi = [], []
    for fonte, falso, vero in dati:
        veri.append(uno(fonte, vero))
        falsi.append(uno(fonte, falso))
    return veri, falsi


def punteggi_hf(nome: str, dati) -> tuple[list[float], list[float]]:
    """Probabilita' di ENTAILMENT della coppia (fonte, claim).

    ⚠️ L'indice della classe «entailment» NON e' lo stesso nei tre modelli: si
    legge da `config.id2label` invece di cablare un intero. Un indice sbagliato
    darebbe un AUROC quasi perfetto ROVESCIATO, ed e' il modo piu' silenzioso di
    sbagliare questo banco.
    """
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(nome)
    mod = AutoModelForSequenceClassification.from_pretrained(nome).eval()
    etichette = {i: str(v).lower() for i, v in mod.config.id2label.items()}
    idx = next((i for i, v in etichette.items() if "entail" in v), None)
    if idx is None:
        idx = max(etichette) if len(etichette) > 1 else 0
    print(f"      id2label={etichette}  ->  entailment = classe {idx}", flush=True)

    def punteggio(premessa: str, ipotesi: str) -> float:
        with torch.no_grad():
            out = mod(**tok(premessa, ipotesi, return_tensors="pt",
                            truncation=True, max_length=512)).logits[0]
        return float(torch.softmax(out, dim=-1)[idx])

    veri = [punteggio(f, v) for f, _, v in dati]
    falsi = [punteggio(f, x) for f, x, _ in dati]
    # niente `del`: `punteggio` e una chiusura su mod e tok, cancellarli qui
    # romperebbe la funzione se qualcuno la riusasse fuori da queste due righe.
    return veri, falsi


def tabella(titolo: str, esiti: dict[str, tuple[list[float], list[float]]]) -> None:
    intest = "  ".join(f"{int(100 * q):>3d}%" for q in QUOTE)
    print(f"\n── {titolo}")
    print(f"{'scorer':28s} {'AUROC':>7s}   falsi fermati su 30 a pari veri persi: {intest}")
    print("-" * 86)
    for nome, (veri, falsi) in esiti.items():
        a = auroc(veri, falsi)
        colonne = "  ".join(f"{falsi_fermati(veri, falsi, q):>4d}" for q in QUOTE)
        print(f"{nome:28s} {a:>7.4f}   {'':>38s}{colonne}")


def main() -> None:
    dati = casi()
    #: la seconda condizione: stessa fonte con UNA frase estranea in coda. E' la
    #: popolazione DURA — quella dove il nostro giudice passa da 0,73 a 32,11 e
    #: su certi claim da 1,84 a 99,94 (banco `ws3-quali-claim-la-zavorra-...`).
    zavorra = "La mensa aziendale resta chiusa il primo maggio."
    duri = [(f"{f} {zavorra}", x, v) for f, x, v in dati]

    print(f"BANCO ws3-P1/P2 — {len(dati)} coppie x 2 condizioni, italiano\n")
    corta: dict[str, tuple[list[float], list[float]]] = {}
    dura: dict[str, tuple[list[float], list[float]]] = {}

    print("  R il nostro giudice (CE locale)", flush=True)
    corta["R nostro giudice"] = punteggi_nostro(dati)
    dura["R nostro giudice"] = punteggi_nostro(duri)
    for etichetta, nome in MODELLI.items():
        print(f"  {etichetta}  ({nome})", flush=True)
        try:
            corta[etichetta] = punteggi_hf(nome, dati)
            dura[etichetta] = punteggi_hf(nome, duri)
        except Exception as e:  # noqa: BLE001
            print(f"      🔴 NON MISURATO: {type(e).__name__}: {e}")

    tabella("FONTE CORTA", corta)
    tabella("FONTE + FRASE ESTRANEA (popolazione dura)", dura)

    print("\n── P2: quanto costa la frase estranea a ciascuno")
    for nome in corta:
        if nome not in dura:
            continue
        a_c, a_d = auroc(*corta[nome]), auroc(*dura[nome])
        d = a_d - a_c
        print(f"  {nome:28s} {a_c:.4f} -> {a_d:.4f}   ({d:+.4f})  "
              + ("🔴 perde >= 0,05" if d <= -0.05 else "regge"))

    print()
    if "R nostro giudice" in corta:
        rif = auroc(*corta["R nostro giudice"])
        for chiave, pred in (("A nli-deberta-v3-base", "①"),
                             ("B deberta-large-mnli-fever", "①"),
                             ("C MiniCheck-DeBERTa-large", "②")):
            if chiave in corta:
                a = auroc(*corta[chiave])
                d = a - rif
                print(f"  P1{pred} {chiave:28s} AUROC {a:.4f} contro R {rif:.4f} "
                      f"({d:+.4f})  "
                      + ("🔴 SUPERA R di >=0,05" if d >= 0.05 else "sotto o pari a R"))
        peggio = max((falsi_fermati(v, f, 0.10) for v, f in corta.values()), default=0)
        print(f"  P1③ massimo falsi fermati al 10% di veri persi: {peggio}/30  "
              + ("🔴 BANCO SATURO (>=28): non decide niente"
                 if peggio >= 28 else "✅ il banco discrimina"))
        alti = [n for n in ("B deberta-large-mnli-fever", "C MiniCheck-DeBERTa-large")
                if n in dura and auroc(*dura[n]) >= 0.95]
        print("  P2② almeno uno fra B e C >= 0,95 con la zavorra: "
              + (f"✅ {alti}" if alti else "🔴 FALSIFICATA, scendono entrambi"))


if __name__ == "__main__":
    main()
