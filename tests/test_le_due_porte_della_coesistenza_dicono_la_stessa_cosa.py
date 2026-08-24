"""Un verdetto emesso da due porte deve avere UNA spiegazione, non due.

Il gate emette alcuni verdetti da **due** punti diversi di
`anti_confab_gate.py`, e quei punti avevano ciascuno il proprio testo. Su
`L3-coexistence` i due testi erano già divergiti, e arrivavano **entrambi
nella stessa ricevuta**::

    L3-coexistence  ...a distinct code, date, numbered record,
                    ATTRIBUTE OR PROPER NAME — so neither is an update...
    L3-coexistence  ...a distinct code, date, OR NAMED RECORD - so
                    neither supersedes the other...

⚠️ La seconda ometteva il nome proprio, che è il ramo che scatta di più
(`if ea or eb` in `_entita_diverse`). Chi la legge cerca un codice o una data,
non li trova, e conclude che il gate ha sbagliato — è il caso portato da ws7.

🪞 E LA PRIMA CURA ERA INCOMPLETA, per una ragione che vale più del difetto.
Alle 20:54 avevo unificato l'advice di `L3-coexistence` e mi ero fermata lì,
senza chiedermi **quali ALTRI verdetti uscissero doppi**. Misurato dopo, alla
porta, su cinque casi che accendono layer diversi::

    L3-coexistence    2 warning   <- curato
    L3-supersession   2 warning   <- IL GEMELLO, rimasto scoperto
    L1.10/L1.15/L1.20 1 ciascuno
    L4.1/L4-grounding 1 ciascuno

`L3-supersession` aveva le stesse due copie letterali, **oggi identiche** — e
due copie identiche sono solo due copie che non hanno ancora divergiuto: è da
lì che era partita la coesistenza. In più il `reason` era duplicato in
entrambi i layer, compreso quello già curato.

🔑 IL PRESIDIO VECCHIO NON L'AVREBBE PRESO: guardava `L3-coexistence` per
nome. Quello qui sotto è generale — **se un layer è emesso da due o più punti,
nessuno dei due può cablare il testo** — e sarebbe stato rosso su
`L3-supersession` prima di questa cura.

⛔ COSA QUESTA CURA NON FA: non cambia il comportamento (solo i testi), non
rende verde `test_l3_subject_prefilter::head_mismatch_never_skipped` (di ws7,
riguarda lo skip), e **non toglie il duplicato** — i verdetti escono ancora
due volte. Allineati sono ridondanti anziché contraddittori; deduplicare
cambia il numero di warning ed è una decisione separata, dichiarata e non
presa.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

import pytest

from verimem import Memory

_GATE = Path(__file__).resolve().parent.parent / "verimem" / "anti_confab_gate.py"

#: (layer, fatti da scrivere prima, scrittura che accende il verdetto)
CASI = [
    ("L3-coexistence",
     [("The payments team still runs on the legacy processor.",
       "Minutes: the payments team still runs on the legacy processor.")],
     "The payments team migrated to Stripe in 2025.",
     "Minutes: the payments team migrated to Stripe in 2025."),
    ("L3-supersession",
     [("Il magazzino nord ha 1800 metri quadrati.",
       "Planimetria: magazzino nord, 1800 metri quadrati.")],
     "Il magazzino nord ha 2500 metri quadrati.",
     "Planimetria aggiornata: magazzino nord, 2500 metri quadrati."),
]


def _avvisi(tmp_path, layer, prima, proposition, source):
    m = Memory(str(tmp_path / "s.db"))
    for p, s in prima:
        m.add(p, topic="t", source=s)
    r = m.add(proposition, topic="t", source=source)
    return [w for w in (r.get("warnings") or []) if str(w.get("layer")) == layer]


@pytest.mark.parametrize(("layer", "prima", "prop", "src"), CASI,
                         ids=[c[0] for c in CASI])
def test_un_verdetto_ha_una_sola_spiegazione(tmp_path, layer, prima, prop, src):
    """IL CUORE, alla PORTA: qualunque sia il numero di warning, il verdetto
    deve avere UN reason e UN advice. Vale per ENTRAMBI i layer emessi due
    volte — la prima stesura provava solo il primo."""
    av = _avvisi(tmp_path, layer, prima, prop, src)
    if not av:
        pytest.skip(f"il banco non accende {layer} in questo ambiente")
    for campo in ("reason", "advice"):
        testi = {str(w.get(campo) or "") for w in av}
        assert len(testi) == 1, (
            f"{layer} arriva con {len(testi)} `{campo}` DIVERSI nella stessa "
            f"ricevuta: {[t[:80] for t in sorted(testi)]}")


def test_la_coesistenza_nomina_il_ramo_che_scatta_di_piu(tmp_path):
    """Un consiglio che elenca le cause deve elencare QUELLA che ha deciso.

    Qui il gate ha trattenuto per un NOME PROPRIO («Stripe», su un lato solo):
    un testo che parla solo di «codice, data, record nominato» manda a cercare
    tre cose che nel caso non ci sono."""
    layer, prima, prop, src = CASI[0]
    av = _avvisi(tmp_path, layer, prima, prop, src)
    if not av:
        pytest.skip("il banco non accende L3-coexistence in questo ambiente")
    for w in av:
        assert "proper name" in str(w.get("advice") or ""), (
            f"il consiglio non nomina il nome proprio, che è la causa di "
            f"questo caso: {w.get('advice')!r}")


def test_nessun_layer_emesso_due_volte_cabla_il_proprio_testo():
    """⚠️ IL PRESIDIO STRUTTURALE, sui verdetti DICHIARATI.

    La prima versione nominava `L3-coexistence` e per questo non ha visto
    `L3-supersession`, che aveva lo stesso difetto a venti righe di distanza.

    🪞 POI L'HO GENERALIZZATA A «ogni layer emesso da due o più punti», ed
    era TROPPO LARGA: accusava codice CORRETTO. Misurato — il presidio
    generale diventava rosso su tre layer, e il primo che ho aperto era::

        L4-skipped, se `judge_state() == "warming"`:
            «il giudice si sta caricando — NON è mancante»
        L4-skipped, altrimenti:
            «il modello non è installato — esegui `verimem warmup`»

    Due testi diversi **di proposito**: due cause diverse, due rimedi
    diversi. Non è una copia divergente.
    ⇒ 🔑 Un criterio SINTATTICO (stesso layer, due punti) su un fenomeno
    SEMANTICO (è lo stesso verdetto?) sbaglia in ENTRAMBE le direzioni. La
    differenza non sta nel layer: sta in se le due situazioni siano la
    stessa, e quello l'AST non lo vede.

    ⇒ Il criterio qui è quindi la LISTA DICHIARATA: i verdetti che
    `_TESTI_VERDETTO_L3` afferma avere un testo solo. Aggiungere un layer al
    dizionario lo mette automaticamente sotto presidio.

    ⛔ APERTO, misurato e NON chiuso restringendo: `L4-grounding-graded`
    (righe ~2551 e ~2639) e `L4-grounding` (~2651) hanno anch'essi più punti
    con `advice` letterale. `L4-grounding-graded` porta un `reason` DINAMICO
    e un commento che dice «coherence with the main sub-threshold branch»:
    può essere voluto come `L4-skipped` oppure no. **Non l'ho classificato,
    quindi non lo accuso** — e non lo nascondo.

    ⛔ AST, non regex: questi dict sono annidati dentro `warnings.append(...)`
    e una regex su una struttura annidata legge quello che capita.
    """
    import verimem.anti_confab_gate as G
    dichiarati = set(G._TESTI_VERDETTO_L3)

    albero = ast.parse(_GATE.read_text(encoding="utf-8", errors="replace"))
    per_layer = defaultdict(list)
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Dict):
            continue
        coppie = {getattr(k, "value", None): v
                  for k, v in zip(nodo.keys, nodo.values, strict=False)}
        strato = coppie.get("layer")
        if not (isinstance(strato, ast.Constant)
                and isinstance(strato.value, str)):
            continue
        if strato.value not in dichiarati:
            continue
        letterali = [c for c in ("reason", "advice")
                     if isinstance(coppie.get(c), ast.Constant)
                     and isinstance(coppie[c].value, str)]
        per_layer[strato.value].append((nodo.lineno, letterali))

    colpevoli = {
        layer: [(riga, campi) for riga, campi in punti if campi]
        for layer, punti in per_layer.items()
    }
    colpevoli = {k: v for k, v in colpevoli.items() if v}
    assert not colpevoli, (
        f"questi verdetti dichiarati in `_TESTI_VERDETTO_L3` cablano di nuovo "
        f"il testo invece di leggerlo dal dizionario: {colpevoli}. Due copie "
        f"ri-divergono — è successo su L3-coexistence senza che nessun test le "
        f"confrontasse.")


def test_i_testi_condivisi_non_restano_orfani():
    """Il controllo dell'altro verso, e senza di esso il presidio si aggira.

    Cancellare gli usi renderebbe verde il test qui sopra: il modo più facile
    di far passare un presidio è togliere ciò che presidia.
    """
    src = _GATE.read_text(encoding="utf-8", errors="replace")
    usi = src.count("_TESTI_VERDETTO_L3")
    assert usi >= 5, (
        f"`_TESTI_VERDETTO_L3` compare {usi} volte: attese almeno 5 — la "
        f"definizione e i QUATTRO punti che emettono i due verdetti")
    import verimem.anti_confab_gate as G
    for layer in ("L3-coexistence", "L3-supersession"):
        voce = G._TESTI_VERDETTO_L3.get(layer) or {}
        assert voce.get("reason") and voce.get("advice"), (
            f"il verdetto {layer} ha perso reason o advice: {voce!r}")
