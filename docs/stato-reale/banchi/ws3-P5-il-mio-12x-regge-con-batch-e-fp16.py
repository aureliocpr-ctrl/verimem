"""LIVELLO: lo scorer B da solo — si misura la sua latenza, non il gate.

Il 12,30x che ho misurato io regge con batching e in fp16?

    python docs/stato-reale/banchi/ws3-P5-il-mio-12x-regge-con-batch-e-fp16.py

⚠️ Carica il modello quattro volte (un regime per volta). Serve uno slot.

━━ PERCHE' ESISTE, ed e' un banco contro un numero MIO ━━━━━━━━━━━━━━━━━━━━━━
`ws3-P4-...` ha misurato che B costa 2084,4 ms a coppia contro i 169,4 del
nostro CE: **12,30x**. Quel numero sta per chiudere la decisione sul modello, e
l'ho preso io in una condizione che ho dichiarato — CPU, una coppia alla volta,
fp32, senza batching — ma che nessuno ha ancora provato a smontare. Lo smonto
io: se il 12,30x e' un artefatto del mio disegno, chi decide deve saperlo prima
di scartare B per la latenza.

━━ IL CONTROLLO CHE STA ACCANTO ALLA VELOCITA', e non dopo ━━━━━━━━━━━━━━━━━━
Ogni regime riporta anche la FEDELTA': scarto massimo dei punteggi rispetto al
regime 1 e AUROC ricalcolato. Un'accelerazione che sposta il verdetto non e'
un'accelerazione, e' un'altra misura.
Il 2026-09-02 ho misurato int8 sul giudice attuale: 2,1-2,4x piu' veloce e
**meno 30 punti** di falsi fermati. Senza il controllo di fedelta' quel banco
avrebbe consegnato «int8 e' due volte piu' veloce» e sarebbe stato vero e
inutile.

━━ PREDIZIONE ws3-P5, depositata sul canale prima di eseguire ━━━━━━━━━━━━━━━
 ① batch 8 in fp32 da' >= 3x per coppia  🔴 sotto 3x: il collo e' il calcolo e
    il 12,30x e' un limite vero, non un artefatto mio
 ② fp16 su CPU NON accelera (< 1,3x), e potrebbe rallentare — contro
    l'intuizione «meta' precisione, doppia velocita'»  🔴 muore a >= 1,3x
 ③ fedelta': scarto massimo < 0,01 e AUROC entro 0,02  🔴 se un regime veloce
    sposta l'AUROC, quel regime non e' utilizzabile

━━ MISURATO IL 2026-09-04 alle 19:24 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    regime                     ms/coppia  x su reg.1    AUROC  scarto max
    0  il nostro CE                448.6          —        —          —
    1  fp32, una alla volta       3503.7       1.00x   0.9444    0.00000
    2  fp32, batch 8              1880.4       1.86x   0.9444    0.00161
    3  fp16, una alla volta       3588.7       0.98x   0.9444    0.00000
    4  fp16, batch 8              1853.4       1.89x   0.9444    0.00161

    rapporti NELLA STESSA CONDIZIONE (nostro CE = 448,6 ms):
      fp32 una alla volta  7,81x      fp32 batch 8  4,19x
      fp16 una alla volta  8,00x      fp16 batch 8  4,13x

 ① batch 8 >= 3x   🔴 FALSIFICATA: 1,86x. Il collo NON e' l'overhead
    per-chiamata, e' il calcolo: il divario si riduce ma non sparisce.
 ② fp16 non accelera su CPU   ✅ CONFERMATA: 0,98x, cioe' un filo piu' LENTO.
    Su x86 i kernel nativi in mezza precisione non ci sono e il tipo viene
    convertito. E' contro l'intuizione «meta' precisione, doppia velocita'».
 ③ fedelta'   ✅ CONFERMATA: AUROC **0,9444 identico in tutti e quattro** i
    regimi, scarto massimo 0,00161. Al contrario di int8 sul nostro giudice
    (02/09: 2,4x piu' veloce e MENO 30 punti).

🔴 E CORREGGE UN NUMERO MIO: `ws3-P4-...` diceva **12,30x**. Il rapporto vero,
misurato con il riferimento DENTRO questo impianto, e' **7,81x** senza batch e
**4,19x** con batch 8. P4 misurava il tempo ripetendo DIECI VOLTE LA STESSA
coppia: ripetere un input non misura la latenza di un giudice, misura il suo
percorso caldo su un input solo, e avvantaggia il nostro CE (169,4 ms li',
448,6 ms qui su coppie tutte diverse) piu' di quanto avvantaggi B.

⚠️ I MILLISECONDI ASSOLUTI NON SONO STABILI: due esecuzioni di questo stesso
banco a pochi minuti di distanza danno 1664,8 e 3503,7 ms per il regime 1 — la
macchina e' condivisa con altri banchi. **Dentro una singola esecuzione il
rapporto regge**, ed e' l'unica quantita' che va letta. Un tempo assoluto preso
qui e citato altrove sarebbe un numero senza il suo carico.

⇒ PER LA DECISIONE: B costa **~4,2x** il giudice attuale con batch 8, non
dodici. Il compromesso resta, ma e' un altro compromesso.

━━ CIO' CHE NON DECIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CPU, questa macchina carica, questi 60 casi italiani. Niente GPU, niente ONNX,
niente daemon condiviso. E la fedelta' e' sui PUNTEGGI: qui reggono, quindi il
batch 8 e' utilizzabile senza rifare P3 — ma se un giorno un regime spostasse
l'AUROC, P3 andrebbe rifatto con quel regime prima di fidarsi.
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path

QUI = Path(__file__).resolve().parent
MODELLO = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"


def casi() -> list[tuple[str, str, str]]:
    s = importlib.util.spec_from_file_location(
        "_impl", QUI / "ws3-P3-la-popolazione-implicita-contro-quattro-scorer.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m.casi()


def auroc(pos: list[float], neg: list[float]) -> float:
    vinte = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return vinte / (len(pos) * len(neg))


def punteggi(coppie: list[tuple[str, str]], mezza: bool, lotto: int) -> tuple[list[float], float]:
    """Punteggi di entailment e secondi PER COPPIA, in un regime solo.

    ⚠️ L'indice di «entailment» si legge da `config.id2label` (per questo
    modello e' 0): cablarlo darebbe un AUROC rovesciato.
    ⚠️ Il caricamento sta FUORI dal cronometro: qui si misura l'inferenza, e
    P4 ha gia' misurato il carico (50,5 s).
    """
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODELLO)
    mod = AutoModelForSequenceClassification.from_pretrained(MODELLO).eval()
    if mezza:
        mod = mod.half()
    etichette = {i: str(v).lower() for i, v in mod.config.id2label.items()}
    idx = next((i for i, v in etichette.items() if "entail" in v), max(etichette))

    fuori: list[float] = []
    t0 = time.perf_counter()
    for i in range(0, len(coppie), lotto):
        pezzo = coppie[i:i + lotto]
        x = tok([p for p, _ in pezzo], [h for _, h in pezzo], return_tensors="pt",
                truncation=True, max_length=512, padding=True)
        with torch.no_grad():
            out = mod(**x).logits
        fuori.extend(float(v) for v in torch.softmax(out.float(), dim=-1)[:, idx])
    return fuori, (time.perf_counter() - t0) / len(coppie)


def main() -> None:
    dati = casi()
    #: prima tutti i VERI poi tutti i FALSI: l'ordine e' fisso in ogni regime,
    #: cosi' i punteggi sono confrontabili posizione per posizione
    coppie = [(f, v) for f, _, v in dati] + [(f, x) for f, x, _ in dati]
    n = len(dati)
    print(f"IL MIO 12,30x REGGE? — {len(coppie)} coppie, quattro regimi\n")
    print(f"{'regime':28s} {'ms/coppia':>11s} {'x su reg.1':>11s} "
          f"{'AUROC':>8s} {'scarto max':>11s}")
    print("-" * 74)

    # ⚠️ IL RIFERIMENTO SI MISURA QUI DENTRO, sulle STESSE 60 coppie e nello
    # stesso processo. P4 aveva misurato il nostro CE a 169,4 ms e B a 2084,4,
    # ma in un altro impianto (dieci ripetizioni di UNA coppia, in un
    # sottoprocesso): confrontare quel 169,4 con i millisecondi di questo banco
    # mescolerebbe due condizioni, ed e' l'errore che ho fatto il 03/09 quando
    # opposi 2,4 s a 41 s misurando due grandezze diverse.
    print("0  il nostro CE, stesse coppie", flush=True)
    from verimem.local_grounding import try_local_score
    t0 = time.perf_counter()
    for premessa, ipotesi in coppie:
        try_local_score(premessa, ipotesi)
    nostro_ms = (time.perf_counter() - t0) / len(coppie) * 1000
    print(f"{'0  nostro CE (riferimento)':28s} {nostro_ms:>10.1f} "
          f"{'—':>10s} {'—':>8s} {'—':>11s}\n", flush=True)

    riferimento: list[float] | None = None
    base_ms = None
    rapporti: list[tuple[str, float]] = []
    for nome, mezza, lotto in [("1  fp32, una alla volta", False, 1),
                               ("2  fp32, batch 8", False, 8),
                               ("3  fp16, una alla volta", True, 1),
                               ("4  fp16, batch 8", True, 8)]:
        try:
            p, sec = punteggi(coppie, mezza, lotto)
        except Exception as e:  # noqa: BLE001
            print(f"{nome:28s} 🔴 NON MISURATO: {type(e).__name__}: {e}")
            continue
        ms = sec * 1000
        if riferimento is None:
            riferimento, base_ms = p, ms
            scarto = 0.0
        else:
            scarto = max(abs(a - b) for a, b in zip(p, riferimento, strict=True))
        a = auroc(p[:n], p[n:])
        rapporti.append((nome, ms))
        print(f"{nome:28s} {ms:>10.1f} {base_ms / ms:>10.2f}x {a:>8.4f} "
              f"{scarto:>11.5f}", flush=True)
        if nome.startswith("2"):
            print("     ① batch 8 >= 3x: "
                  + ("✅" if base_ms / ms >= 3 else "🔴 FALSIFICATA")
                  + f"  ({base_ms / ms:.2f}x)")
        if nome.startswith("3"):
            print("     ② fp16 NON accelera (< 1,3x): "
                  + ("✅" if base_ms / ms < 1.3 else "🔴 FALSIFICATA")
                  + f"  ({base_ms / ms:.2f}x)")
        if scarto > 0.01:
            print(f"     ③ 🔴 FEDELTA' ROTTA: scarto massimo {scarto:.5f} > 0,01 — "
                  "questo regime non e' utilizzabile senza rifare P3")

    print(f"\n  RAPPORTI NELLA STESSA CONDIZIONE (nostro CE = {nostro_ms:.1f} ms):")
    for nome, ms in rapporti:
        print(f"    {nome:26s} {ms / nostro_ms:>6.2f}x il nostro")
    print("\n  ⚠️ P4 aveva misurato 169,4 ms per il nostro CE e 2084,4 per B in un")
    print("     ALTRO impianto (dieci ripetizioni di UNA coppia, in sottoprocesso).")
    print("     I due impianti non si mescolano: il rapporto valido e' quello qui")
    print("     sopra, misurato sulle stesse coppie nello stesso processo.")


if __name__ == "__main__":
    main()
