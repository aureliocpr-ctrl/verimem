"""LA TERZA MAPPA: dove il giudizio dei test diverge da quello del prodotto.

PERCHÉ ESISTE, misurato il 2026-08-04. Curando il caso del fatto che ne aveva
superseduti dodici, il primo banco passava — e non perché la cura ci fosse. La
sonda dentro pytest:

    SOTTO PYTEST  coseno = 0.1974      (stesse due frasi, fuori: 0.8265)

⚠️ LA CAUSA NON È ``HIPPO_OFFLINE``, e la prima versione di questo file lo
diceva sbagliato. Girando lo script con ``--offline`` il massimo raggiungibile
è **0.9872** e ogni soglia del prodotto è alla portata: offline vuol dire solo
che il modello si carica dalla cache locale, e resta il modello vero. A
sostituire l'embedder è ``tests/conftest.py``, con la fixture
``_stub_embedding_model`` che rimpiazza ``embedding._model()`` con uno stub
deterministico costruito su SHA-256 dei token. È una scelta legittima e
dichiarata — test veloci, riproducibili, senza rete — ma ha una conseguenza
che nessuno aveva misurato: **quel coseno riflette la sovrapposizione di
token, non il significato**. Su otto frasi, 28 coppie:

    min 0.0000   mediana 0.0000   MAX 0.8333
    «Il piano annuale costa 100 euro» vs «…120 euro»  ->  0.8333  (vero ~0.97)
    «The drug reduces…» vs «…does not reduce…»        ->  0.6761  (vero ~0.94)

IL VERDETTO UTILE NON È «raggiungibile o no» — con frasi abbastanza simili
qualunque soglia si raggiunge, e la prima versione di questo script rispondeva
appunto «0 soglie su 20 fuori portata», che è vero e non serve a niente. La
domanda che conta è: **su una data soglia, i due regimi darebbero lo stesso
verdetto?** Dove divergono, un test non misura il prodotto: misura lo stub.

Misurato alla soglia 0.75, quella di ``detect_boolean_clashes``:

     reale    stub       Δ    verdetto          caso
    0.9730  0.8333  -0.1397  concordi          stesso soggetto, valore diverso
    0.9872  0.9258  -0.0614  concordi          stesso soggetto, riformulato
    0.9479  0.8660  -0.0819  concordi          idem, in inglese
    0.9275  0.6761  -0.2514  DIVERGE (sì→no)   polarità opposta
    0.8031  0.0000  -0.8031  DIVERGE (sì→no)   niente in comune

La riga che chiude la catena è la quarta. «Polarità opposta» è ESATTAMENTE il
caso di ``detect_boolean_clashes``: col modello vero il coseno sta a 0.9275,
sopra la soglia, e il giudizio si esegue; con lo stub sta a 0.6761, sotto, e il
ramo non viene mai raggiunto. Ecco perché nessun test poteva accorgersi che
quel rilevatore segnalava conflitti fra fatti che parlano d'altro.

Lo stub sottostima sempre (Δ negativo ovunque) perché misura la sovrapposizione
di TOKEN: due frasi senza parole in comune danno esattamente 0, e con un hash è
inevitabile. Non è un difetto dello stub — serve, ed è documentato — è che
nessuno aveva misurato di quanto sposta i verdetti.

È la stessa forma delle altre due mappe: `mappa_ignoranza_delle_misure.py`
chiede «lungo quale dimensione non abbiamo mai misurato», `matrice_delle_
superfici.py` chiede «quale superficie non espone questa capacità». Questa
chiede **«dove il banco di prova giudica diversamente dal prodotto»**.

⚠️ LIMITE: il banco è cinque coppie scritte a mano. Dice che la divergenza
ESISTE e dove colpisce, non quanto sia diffusa nel prodotto — per quello
servirebbero le coppie vere del corpus.

Uso:  python scripts/mappa_delle_soglie_semantiche.py
      python scripts/mappa_delle_soglie_semantiche.py --soglia 0.86
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent

#: Le frasi del banco. Le coppie che contano sono composte sotto, in COPPIE.
SONDE = [
    "Il piano annuale costa 100 euro.",
    "Il piano annuale costa 120 euro.",
    "Il piano annuale costa 100 euro esatti.",
    "The read latency is 5 ms.",
    "The read latency is 9 ms.",
    "The drug reduces patient mortality.",
    "The drug does not reduce patient mortality.",
    "Roma e' la capitale d'Italia.",
]

#: `nome = 0.85` accanto a una parola che indica similarità.
_SOGLIA = re.compile(
    r"^\s*(?:#:\s*)?(\w*(?:similarity|cosine|cluster|dedup|merge|proactive|"
    r"align|schema)\w*)\s*(?::\s*float\s*)?=\s*(0\.\d+)", re.I | re.M)
#: `similarity_threshold: float = 0.75` nelle firme.
_PARAM = re.compile(r"(\w*(?:similarity|cosine)\w*)\s*:\s*float\s*=\s*(0\.\d+)",
                    re.I)


def soglie_dichiarate() -> list[tuple[str, str, float]]:
    fuori: list[tuple[str, str, float]] = []
    for f in sorted((RADICE / "verimem").rglob("*.py")):
        testo = f.read_text(encoding="utf-8", errors="replace")
        for rx in (_SOGLIA, _PARAM):
            for m in rx.finditer(testo):
                voce = (f.relative_to(RADICE).as_posix(), m.group(1),
                        float(m.group(2)))
                if voce not in fuori:
                    fuori.append(voce)
    return fuori


def _installa_stub_del_conftest() -> None:
    """Lo STESSO stub che la suite installa, importato da lì e non riscritto.

    Riscriverlo qui significherebbe misurare una copia: se un domani il
    conftest cambia il suo, questa mappa continuerebbe a rispondere sul
    vecchio — la classe «una copia invece della superficie unica», che questo
    progetto paga da giorni. Quindi si importa il modulo dei test e si usa il
    suo `_StubModel`.
    """
    # Come fa il conftest: senza questo `encode` passa dal SERVIZIO di encoding
    # condiviso e non tocca mai `_model`, quindi lo stub non morde e la misura
    # torna «nessuna divergenza» — un successo per il motivo sbagliato, che è
    # il modo in cui questo stesso file ha gia' sbagliato due volte oggi.
    os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
    os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
    sys.path.insert(0, str(RADICE / "tests"))
    import conftest  # type: ignore[import-not-found]

    from verimem import embedding
    stub = conftest._StubModel()
    embedding._model = lambda: stub          # type: ignore[assignment]
    embedding._MODEL = stub                  # type: ignore[attr-defined]
    # La LRU va svuotata, altrimenti le prime letture restituiscono i vettori
    # del modello VERO e la misura dice «nessuna divergenza» — successo per il
    # motivo sbagliato, che è il modo in cui questo file ha già sbagliato una
    # volta oggi.
    embedding._cached_encode.cache_clear()   # type: ignore[attr-defined]


#: Coppie con l'esito ATTESO dal significato. È il banco su cui si misura la
#: divergenza: non «quanto valgono i coseni» ma «i due regimi darebbero lo
#: stesso VERDETTO a una soglia».
COPPIE = [
    ("stesso soggetto, valore diverso", 0, 1),
    ("stesso soggetto, riformulato", 0, 2),
    ("stesso soggetto, valore diverso (en)", 3, 4),
    ("polarità opposta", 5, 6),
    ("niente in comune", 0, 7),
]


def _coseni(sonde: list[str]) -> list[float]:
    import numpy as np

    from verimem import embedding
    vs = [embedding.encode(s) for s in sonde]

    def cos(a, b):
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = float(np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / d) if d > 0 else 0.0

    return [cos(vs[i], vs[j]) for _, i, j in COPPIE]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--soglia", type=float, default=0.75,
                    help="la soglia su cui confrontare i verdetti (default "
                         "0.75, quella di detect_boolean_clashes)")
    args = ap.parse_args()

    # Prima il modello VERO, poi lo stub: l'ordine conta, lo stub sovrascrive
    # `embedding._model` per il resto del processo.
    reali = _coseni(SONDE)
    _installa_stub_del_conftest()
    stub = _coseni(SONDE)

    s = args.soglia
    print(f"soglia di confronto: {s:.2f}\n")
    print(f"{'reale':>7} {'stub':>7} {'Δ':>8}  {'verdetto':<22} caso")
    divergenti = 0
    for (nome, _, _), r, t in zip(COPPIE, reali, stub, strict=True):
        vr, vt = r >= s, t >= s
        if vr != vt:
            divergenti += 1
            verdetto = f"DIVERGE ({'sì' if vr else 'no'}→{'sì' if vt else 'no'})"
        else:
            verdetto = "concordi"
        print(f"{r:>7.4f} {t:>7.4f} {t - r:>+8.4f}  {verdetto:<22} {nome}")

    print(f"\n{divergenti} casi su {len(COPPIE)} ricevono un verdetto DIVERSO "
          f"alla soglia {s:.2f}.")
    print("Su quei casi un test non misura il comportamento del prodotto: "
          "misura lo stub.")

    print("\n--- le soglie dichiarate nel prodotto, per sapere chi è esposto ---")
    for f, n, v in sorted(soglie_dichiarate(), key=lambda x: -x[2]):
        print(f"{v:>7.2f}  {f}:{n}")
    print("\nRimedio, quello usato in test_il_vincitore_che_ne_ingoio_dodici: "
          "fissare il coseno con monkeypatch al valore MISURATO sul corpus, "
          "e giudicare la logica invece del modello.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
