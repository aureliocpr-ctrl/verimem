"""LIVELLO: gli SCORER, non la porta — quattro giudici su contraddizioni IMPLICITE.

    python docs/stato-reale/banchi/ws3-P3-la-popolazione-implicita-contro-quattro-scorer.py

⚠️ Carica quattro scorer, tutti in cache. Serve uno slot di inferenza. ~5 min.

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sulle contraddizioni DIRETTE (`ws3-P1-tre-modelli-...`) B e C fanno AUROC
1,0000 in entrambe le condizioni: il banco satura e non ordina nessuno. Qui si
misura la famiglia dove il nostro gate fallisce davvero.

CHE COSA RENDE UNA COPPIA «IMPLICITA», dichiarato prima dei numeri: il claim
falso NON contiene un negatore, NON e' l'antonimo lessicale del verbo della
fonte, e per vedere che contraddice serve un passo di inferenza su un
QUANTIFICATORE, su una CONSEGUENZA o su una SEQUENZA TEMPORALE.

    fonte  «Il collaudo si e' concluso con tre rilievi minori.»
    falso  «Il collaudo si e' concluso senza rilievi.»      <- «tre» contro «senza»
    vero   «Al collaudo sono emersi dei rilievi.»           <- serve lo stesso passo

━━ IL CONTROLLO CHE PUO' FALSIFICARE QUESTO BANCO, e sta qui apposta ━━━━━━━━
Se i claim VERI somigliassero alla fonte piu' dei FALSI, qualunque modello
vincerebbe guardando la SOVRAPPOSIZIONE DI PAROLE invece dell'inferenza, e il
banco misurerebbe la superficie credendo di misurare il giudizio.

Percio' fra gli scorer c'e' una **linea di base che non capisce niente**:
Jaccard sui token fra fonte e claim. Se ottiene un AUROC alto, il banco e'
contaminato e i confronti fra i quattro non valgono. Si legge PRIMA dei modelli.

━━ PREDIZIONE ws3-P3, depositata sul canale prima di eseguire ━━━━━━━━━━━━━━━
 ① la linea di base lessicale sta SOTTO 0,70   🔴 sopra ⇒ banco contaminato,
    e questa predizione governa le altre due
 ② B e C perdono >= 0,10 rispetto a 1,0000     🔴 se restano >= 0,95, anche
    l'implicito e' facile per loro e il divario col nostro e' peggiore di P2
 ③ nessuno raggiunge 0,98                      🔴 altrimenti satura di nuovo

━━ MISURATO IL 2026-09-03 alle 22:30 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    scorer                        AUROC          [95%]   falsi fermati: 5% 10% 20% 30%
    0 sovrapposizione lessicale  0.6017 [0.449-0.752]                   10  13  14  14
    R nostro giudice             0.6589 [0.523-0.797]                    0   5  15  15
    A nli-deberta-v3-base        0.6700 [0.528-0.803]                    3   4   7  19
    B deberta-large-mnli-fever   0.9444 [0.877-1.000]                   27  27  27  27
    C MiniCheck-DeBERTa-large    0.7656 [0.628-0.882]                   16  16  21  23

    scarti APPAIATI contro il nostro giudice (95%):
      0 sovrapposizione lessicale  -0.0572  [-0.292, +0.163]  NON DECIDIBILE
      A nli-deberta-v3-base        +0.0111  [-0.121, +0.139]  NON DECIDIBILE
      B deberta-large-mnli-fever   +0.2856  [+0.160, +0.420]  REALE
      C MiniCheck-DeBERTa-large    +0.1067  [-0.071, +0.268]  NON DECIDIBILE

P3① confermata (base 0,6017 < 0,70) · P3② META': C perde 0,2344 ✅, B regge a
0,9444 🔴 · P3③ confermata (massimo 0,9444 < 0,98).

⇒ **UN SOLO CANDIDATO E' DIMOSTRABILMENTE MIGLIORE: B.** +0,2856 con
l'intervallo appaiato che esclude lo zero. C e A non sono distinguibili dal
nostro giudice su questo banco, e chi li scegliesse sceglierebbe su rumore.

⇒ **E IL NOSTRO GIUDICE NON E' DISTINGUIBILE DA UNO SCORER CHE CONTA LE PAROLE
IN COMUNE** (-0,0572, intervallo [-0,292, +0,163] che contiene lo zero).
⚠️ Questo NON significa «e' peggio del conta-parole»: significa che su questo
banco i due non si distinguono, ed e' gia' abbastanza grave da solo. Scrivere
«e' peggio» sarebbe leggere il segno di uno scarto che l'intervallo non decide.

⚠️ IL NUMERO CHE NON HA BISOGNO DELL'INTERVALLO: al 5% di veri persi il nostro
giudice ferma **0 falsi su 30**; B ne ferma 27. E' un punto di lavoro, non una
stima, e il divario non e' interpretabile come rumore.

⚠️ E L'INTERVALLO DI B ARRIVA A 1,000: anche B potrebbe essere vicino al
soffitto qui. Questo banco lo separa dal nostro, NON lo separa da un futuro
candidato migliore — per quello servirebbero casi ancora piu' duri.

━━ CIO' CHE NON DECIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trenta coppie scritte da me, in italiano, in forma di verbale. Non e' un tasso
di prodotto, non dice niente sull'inglese ne' sui testi lunghi, e il costo in
RAM e secondi di B e C resta NON misurato — senza quello «cambiamo modello»
resta una proposta, non una decisione.
⚠️ Trenta contro trenta sono POCHI: gli intervalli sono larghi di proposito e
vanno letti, non saltati. Nel primo giro di questo banco gli intervalli NON
c'erano, e il confronto fra il nostro giudice e la linea di base sembrava
dire qualcosa: non lo diceva.
"""
from __future__ import annotations

import re

QUOTE = [0.05, 0.10, 0.20, 0.30]

MODELLI = {
    "A nli-deberta-v3-base": "cross-encoder/nli-deberta-v3-base",
    "B deberta-large-mnli-fever": "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
    "C MiniCheck-DeBERTa-large": "lytang/MiniCheck-DeBERTa-v3-Large",
}

#: (fonte, claim FALSO, claim VERO). Regole che mi sono dato e che si possono
#: controllare leggendo: nessun negatore nel falso, nessun antonimo del verbo
#: della fonte, e il VERO richiede lo stesso passo di inferenza del falso.
COPPIE = [
    ("Verbale: il collaudo si e' concluso con tre rilievi minori.",
     "Il collaudo si e' concluso senza rilievi.",
     "Al collaudo sono emersi dei rilievi."),
    ("Verbale: il pagamento e' stato sospeso in attesa di verifica.",
     "Il fornitore ha incassato l'importo.",
     "Il fornitore e' ancora in attesa dell'importo."),
    ("Verbale: la riunione e' stata rinviata a data da destinarsi.",
     "Le decisioni sono state assunte in quella riunione.",
     "Nessuna decisione e' stata assunta in quella data."),
    ("Verbale: la consegna e' slittata di due settimane.",
     "La consegna e' avvenuta nei termini previsti.",
     "La consegna e' arrivata dopo la data prevista."),
    ("Verbale: l'impianto lavora al quaranta per cento della capacita'.",
     "L'impianto lavora a pieno regime.",
     "L'impianto lascia inutilizzata piu' di meta' della capacita'."),
    ("Verbale: la pratica e' passata al secondo dei quattro gradi previsti.",
     "L'iter della pratica si e' concluso.",
     "Alla pratica mancano ancora dei gradi."),
    ("Verbale: dei dodici partecipanti ne sono arrivati cinque.",
     "Sono arrivati tutti i partecipanti.",
     "Alcuni partecipanti non sono arrivati."),
    ("Verbale: il tetto e' stato coperto con un telo provvisorio.",
     "Il tetto e' stato riparato in modo definitivo.",
     "Sul tetto serve ancora un intervento."),
    ("Verbale: la licenza e' valida fino al 31 dicembre 2024.",
     "La licenza copre le attivita' del marzo 2025.",
     "Nel 2025 la licenza risulta scaduta."),
    ("Verbale: il campione e' stato prelevato ma non ancora analizzato.",
     "Il referto del campione riporta valori nella norma.",
     "Del campione non si conoscono ancora i valori."),
]
SOGGETTI = ["Il responsabile", "L'ufficio tecnico", "La direzione"]


def casi() -> list[tuple[str, str, str]]:
    """Trenta: dieci schemi x tre varianti di soggetto nel verbale."""
    fuori = []
    for i, (fonte, falso, vero) in enumerate(COPPIE):
        for k in range(3):
            chi = SOGGETTI[(i + k) % 3]
            fuori.append((fonte.replace("Verbale:", f"Verbale di {chi.lower()}:"),
                          falso, vero))
    return fuori[:30]


def auroc(pos: list[float], neg: list[float]) -> float:
    """P(punteggio di un VERO > punteggio di un FALSO). Mann-Whitney, pari 0,5."""
    if not pos or not neg:
        return float("nan")
    vinte = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return vinte / (len(pos) * len(neg))


def falsi_fermati(veri: list[float], falsi: list[float], quota: float) -> int:
    ordinati = sorted(veri)
    i = min(len(ordinati) - 1, max(0, int(round(quota * len(ordinati)))))
    return sum(1 for f in falsi if f < ordinati[i])


def intervallo(veri: list[float], falsi: list[float],
               giri: int = 2000) -> tuple[float, float]:
    """Intervallo al 95% dell'AUROC, per ricampionamento delle DUE popolazioni.

    ⚠️ STA QUI PERCHE' MANCAVA ALLA MIA PREDIZIONE. Con trenta contro trenta un
    AUROC ha un'incertezza dell'ordine di 0,06-0,07: leggere «0,6589 contro
    0,6017» come «il nostro giudice batte il conteggio di parole» sarebbe
    leggere del rumore. Il numero da solo non basta, e il modo di accorgersene
    va scritto nel banco, non lasciato al lettore.
    """
    import random
    r = random.Random(20260903)
    valori = []
    for _ in range(giri):
        v = [r.choice(veri) for _ in veri]
        f = [r.choice(falsi) for _ in falsi]
        valori.append(auroc(v, f))
    valori.sort()
    return valori[int(0.025 * giri)], valori[int(0.975 * giri) - 1]


def differenza(a: tuple[list[float], list[float]],
               b: tuple[list[float], list[float]],
               giri: int = 2000) -> tuple[float, float]:
    """Intervallo al 95% della DIFFERENZA fra due AUROC, ricampionando le stesse
    unita' per entrambi: e' il confronto APPAIATO, l'unico che risponde a «lo
    scarto esiste?» invece di «i due intervalli si toccano?».
    """
    import random
    r = random.Random(20260903)
    n_v, n_f = len(a[0]), len(a[1])
    valori = []
    for _ in range(giri):
        iv = [r.randrange(n_v) for _ in range(n_v)]
        if_ = [r.randrange(n_f) for _ in range(n_f)]
        va = auroc([a[0][i] for i in iv], [a[1][i] for i in if_])
        vb = auroc([b[0][i] for i in iv], [b[1][i] for i in if_])
        valori.append(va - vb)
    valori.sort()
    return valori[int(0.025 * giri)], valori[int(0.975 * giri) - 1]


def sovrapposizione(a: str, b: str) -> float:
    """Jaccard sui token: la linea di base che NON capisce niente.

    Serve a falsificare il banco, non a giudicare: se separa i veri dai falsi,
    allora le due popolazioni differiscono per SUPERFICIE e non per inferenza.
    """
    ta = set(re.findall(r"\w+", a.lower()))
    tb = set(re.findall(r"\w+", b.lower()))
    return len(ta & tb) / max(1, len(ta | tb))


def punteggi_baseline(dati) -> tuple[list[float], list[float]]:
    return ([sovrapposizione(f, v) for f, _, v in dati],
            [sovrapposizione(f, x) for f, x, _ in dati])


def punteggi_nostro(dati) -> tuple[list[float], list[float]]:
    from verimem.local_grounding import try_local_score

    def uno(fonte: str, claim: str) -> float:
        r = try_local_score(fonte, claim)      # torna (punteggio, soglia) o None
        return float(r[0]) if r is not None else 0.0

    return ([uno(f, v) for f, _, v in dati], [uno(f, x) for f, x, _ in dati])


def punteggi_hf(nome: str, dati) -> tuple[list[float], list[float]]:
    """⚠️ L'indice di «entailment» si LEGGE da `config.id2label`: e' 1, 0 e 1 nei
    tre modelli, e cablarlo darebbe un AUROC quasi perfetto ROVESCIATO.
    """
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(nome)
    mod = AutoModelForSequenceClassification.from_pretrained(nome).eval()
    etichette = {i: str(v).lower() for i, v in mod.config.id2label.items()}
    idx = next((i for i, v in etichette.items() if "entail" in v), max(etichette))
    print(f"      id2label={etichette} -> entailment = {idx}", flush=True)

    def punteggio(premessa: str, ipotesi: str) -> float:
        with torch.no_grad():
            out = mod(**tok(premessa, ipotesi, return_tensors="pt",
                            truncation=True, max_length=512)).logits[0]
        return float(torch.softmax(out, dim=-1)[idx])

    return ([punteggio(f, v) for f, _, v in dati],
            [punteggio(f, x) for f, x, _ in dati])


def main() -> None:
    dati = casi()
    print(f"BANCO ws3-P3 — {len(dati)} coppie IMPLICITE italiane\n")
    esiti: dict[str, tuple[list[float], list[float]]] = {}

    print("  0 linea di base lessicale (Jaccard) — il controllo che puo' falsificare", flush=True)
    esiti["0 sovrapposizione lessicale"] = punteggi_baseline(dati)
    print("  R il nostro giudice (CE locale)", flush=True)
    esiti["R nostro giudice"] = punteggi_nostro(dati)
    for etichetta, nome in MODELLI.items():
        print(f"  {etichetta}", flush=True)
        try:
            esiti[etichetta] = punteggi_hf(nome, dati)
        except Exception as e:  # noqa: BLE001
            print(f"      🔴 NON MISURATO: {type(e).__name__}: {e}")

    intest = "  ".join(f"{int(100 * q):>3d}%" for q in QUOTE)
    print(f"\n{'scorer':30s} {'AUROC':>7s} {'[95%]':>16s}  falsi fermati: {intest}")
    print("-" * 84)
    for nome, (veri, falsi) in esiti.items():
        lo, hi = intervallo(veri, falsi)
        colonne = "  ".join(f"{falsi_fermati(veri, falsi, q):>4d}" for q in QUOTE)
        print(f"{nome:30s} {auroc(veri, falsi):>7.4f} [{lo:.3f}-{hi:.3f}]  "
              f"{'':>13s}{colonne}")

    print("\n  scarti APPAIATI contro il nostro giudice (95%):")
    rif = esiti["R nostro giudice"]
    for nome, e in esiti.items():
        if nome == "R nostro giudice":
            continue
        lo, hi = differenza(e, rif)
        deciso = "REALE" if lo > 0 else ("REALE (sotto)" if hi < 0 else "🔴 NON DECIDIBILE")
        print(f"    {nome:30s} {auroc(*e) - auroc(*rif):+.4f}  "
              f"[{lo:+.3f}, {hi:+.3f}]  {deciso}")

    base = auroc(*esiti["0 sovrapposizione lessicale"])
    print(f"\n  ① linea di base lessicale: {base:.4f}  "
          + ("✅ sotto 0,70: il banco misura inferenza, non superficie"
             if base < 0.70 else
             "🔴 SOPRA 0,70: BANCO CONTAMINATO, i confronti sotto NON valgono"))
    for chiave in ("B deberta-large-mnli-fever", "C MiniCheck-DeBERTa-large"):
        if chiave in esiti:
            a = auroc(*esiti[chiave])
            print(f"  ② {chiave:30s} {a:.4f}  contro 1,0000 delle dirette "
                  f"({a - 1.0:+.4f})  "
                  + ("✅ perde >= 0,10" if a <= 0.90 else "🔴 regge >= 0,90"))
    massimo = max(auroc(v, f) for k, (v, f) in esiti.items()
                  if k != "0 sovrapposizione lessicale")
    print(f"  ③ AUROC massimo fra i quattro scorer: {massimo:.4f}  "
          + ("🔴 SATURO (>=0,98): non ordina" if massimo >= 0.98
             else "✅ il banco discrimina"))


if __name__ == "__main__":
    main()
