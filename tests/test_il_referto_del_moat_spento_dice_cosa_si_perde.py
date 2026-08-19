"""Chi legge «moat OFF» deve sapere che può PERDERE UN FATTO, non solo che non è verificato.

Misurato il 19/08 alle 19:27, eseguendo il Quickstart del README alla lettera in
un venv creato per l'occasione (`pip install` del wheel di `bcc35b5c`, nessuna
cache), su DUE popolazioni che differiscono per una sola cosa — il giudice:

    SENZA giudice                          CON giudice
    ─────────────────────────────────────  ─────────────────────────────────────
    'Analytics runs on Postgres.'  (vero)  'Analytics runs on Postgres.'  (vero)
        RITIRATO                               VIVO, grounding 99.57
        superseded_by = la confabulazione
    'Analytics runs on MongoDB.' (confab)  'Analytics runs on MongoDB.' (confab)
        VIVO — l'unico servito                 QUARANTINED, grounding 0.62
    assert del README: FALLISCE            assert del README: PASSA

⇒ **Con il giudice il prodotto fa esattamente ciò che promette.** Senza, l'esito
non è «meno garanzie»: è ROVESCIATO — la confabulazione ritira il fatto vero e
resta l'unica cosa che un agente ritrova. Il ramo lo dichiara il prodotto stesso
nel suo registro: `flow.supersession branch='same-source evolution'`.

⚠️ E QUI STA IL DIFETTO CHE QUESTO FILE PRESIDIA: entrambe le superfici che
descrivono lo stato «senza giudice» lo raccontavano come una perdita di
VERIFICA, non di DATI.

    doctor  «writes that CARRY A SOURCE are admitted with an L4-skipped
             advisory; writes without a source get no advisory at all»
    README  «Without a judge, writes are admitted WITH an explicit L4-skipped
             advisory (never silently) and the assert below would fail»

Le due frasi sono VERE — misurate riga per riga, l'avviso c'è e l'assert
fallisce davvero. Ma «admitted» descrive ciò che succede alla scrittura nuova, e
tace ciò che succede a quella già in memoria. Chi legge decide se lanciare
`warmup` in base al costo di NON lanciarlo, e quel costo era descritto una
misura più piccola di quello che è.

📌 PERCHÉ IL PRESIDIO STA SUL TESTO E NON SUL COMPORTAMENTO: un collaudo che
verificasse «senza giudice il fatto vero viene ritirato» sarebbe un verde su un
comportamento indesiderato — diventerebbe ROSSO il giorno in cui qualcuno lo
cura, cioè difenderebbe il difetto. Il comportamento è dell'item [1b]
(supersessione), che ha un'altra proprietaria. Ciò che è mio, e che qui si
presidia, è che il prodotto DICA la verità su sé stesso mentre quel
comportamento esiste.

📌 UNA SOLA DEFINIZIONE: `AVVISO_SENZA_GIUDICE` è importata anche da `verimem
warmup` — il commento sopra di essa lo dice e la ragione è che due copie della
stessa frase divergono. Il collaudo interroga quella costante, non il testo
stampato: se qualcuno ne facesse una seconda copia, la copia non verrebbe
sorvegliata da qui e il difetto tornerebbe da quella parte.
"""
from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
README = RADICE / "README.md"

#: Le parole con cui si nomina il fatto che qualcosa di già scritto CADE.
#: Non è un elenco di sinonimi eleganti: è ciò che il lettore deve trovare per
#: capire che il costo non è solo «non verificato».
_PAROLE_DELLA_PERDITA = ("retract", "supersed", "overwrit", "replac")


def _dice_che_si_perde_qualcosa(testo: str) -> bool:
    t = testo.lower()
    return any(p in t for p in _PAROLE_DELLA_PERDITA)


def _commento_del_quickstart() -> str:
    """Il commento che precede `m = Memory("memory.db")` nel Quickstart."""
    testo = README.read_text(encoding="utf-8")
    i = testo.find("## Quickstart (Python)")
    assert i > 0, "il README non ha più un Quickstart in Python"
    j = testo.find('m = Memory("memory.db")', i)
    assert j > i, "il Quickstart non costruisce più una Memory"
    return testo[i:j]


def test_il_referto_di_doctor_dice_che_un_fatto_puo_CADERE():
    """La frase unica che doctor e warmup usano per lo stato «nessun giudice»."""
    from verimem.doctor import AVVISO_SENZA_GIUDICE
    assert _dice_che_si_perde_qualcosa(AVVISO_SENZA_GIUDICE), (
        "il referto dello stato «moat OFF» descrive solo cosa NON viene "
        "verificato, e tace che una scrittura successiva sulla stessa fonte "
        f"ritira quella già in memoria: {AVVISO_SENZA_GIUDICE!r}")


def test_il_quickstart_dice_che_un_fatto_puo_CADERE():
    """La stessa cosa nella vetrina, dove il lettore la incontra per primo."""
    commento = _commento_del_quickstart()
    assert _dice_che_si_perde_qualcosa(commento), (
        "il Quickstart spiega cosa succede senza giudice e non dice che il "
        "fatto vero può essere ritirato dalla confabulazione — che è ciò che "
        "accade eseguendo QUESTO esempio senza `warmup`")


def test_il_criterio_riconoscerebbe_il_difetto():
    """Controllo positivo: sui due testi di PRIMA il criterio deve accusare.

    Senza questo, un criterio che non guarda niente resterebbe verde per sempre
    e sarebbe indistinguibile da uno che funziona.
    """
    doctor_prima = ("writes that CARRY A SOURCE are admitted with an L4-skipped "
                    "advisory; writes without a source get no advisory at all — "
                    "there was nothing to check them against")
    readme_prima = ("Without a judge, writes are admitted WITH an explicit "
                    "L4-skipped advisory (never silently) and the assert below "
                    "would fail — doctor tells you exactly why.")
    assert not _dice_che_si_perde_qualcosa(doctor_prima)
    assert not _dice_che_si_perde_qualcosa(readme_prima)


def test_le_due_superfici_dicono_ancora_che_l_avviso_C_E():
    """La guardia contro la cura sbagliata.

    Il modo più facile di far passare i due test sopra è riscrivere le frasi
    parlando solo del ritiro e togliendo l'avviso L4-skipped. Sarebbe uno
    scambio, non una cura: quell'avviso è misurato e vero, ed è la ragione per
    cui una scrittura senza verifica non entra MAI in silenzio.
    """
    from verimem.doctor import AVVISO_SENZA_GIUDICE
    assert "L4-skipped" in AVVISO_SENZA_GIUDICE, AVVISO_SENZA_GIUDICE
    assert "L4-skipped" in _commento_del_quickstart()
