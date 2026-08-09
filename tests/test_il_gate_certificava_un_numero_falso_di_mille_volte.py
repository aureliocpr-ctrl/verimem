"""«Lo stipendio è 45.000 euro» contro una fonte che dice «45 euro»: AMMESSO.

IL DIFETTO — il peggiore che questo prodotto abbia avuto, trovato la notte del
09→10/08 in tre e da nessuno leggendo il codice. Il gate non taceva e non
accusava a torto: **certificava come vero un fatto che la fonte contraddice di
mille volte**, perché ``float("45.000")`` dà ``45.0``::

    claim «45.000 euro» -> 45.0 ·  fonte «45 euro» -> 45.0 ·  45.0 == 45.0 -> ok

La causa prima è che il punto è ANCHE il separatore decimale inglese, quindi il
pattern lo accetta volentieri e ``float`` restituisce un numero CREDIBILE e
falso. Delle quattro notazioni che rompono l'estrattore (virgola migliaia,
virgola decimale, spazio del SI, punto) questa è l'unica che CERTIFICA: le altre
spezzano il numero, un pezzo non sta nella fonte, e il layer protesta — rumorose
ma oneste. 🔑 **La classe più pericolosa è quella che somiglia di più a una
notazione valida.**

📊 SUL CORPUS REALE (ws8, semantic.db in mode=ro, 9365 proposizioni): la classe
pericolosa è **100 · 1,07%**, l'invisibile («1.500.000» → ``[]``) è **2 · 0,02%**
— CINQUANTA A UNO. Le righe sono nostre: «102.913 LOC» letto 102.9, «16.300+
test pytest verdi» letto 16.3 in tre fatti diversi. ⚠️ ws8 ha letto 6 righe su
100, non tutte.

═══ LA CURA È IN DUE PEZZI, E IL PRIMO DA SOLO NON BASTA ═══

① ``_PUNTO_AMBIGUO`` — sui numeri ambigui NON si emette un valore. Non «vale
   45000», non «vale 45»: si tace sul VALORE, l'unica cosa che si sa per certo
   essere sbagliata. ⚠️ NON è disambiguare: «12,450» vale 12450 in inglese e
   12,45 in italiano, e indovinare significherebbe confrontare due valori diversi
   credendoli uguali — un difetto SILENZIOSO, peggiore di quello curato.

② ``numeri_ambigui`` + il warning ``L4.1-ambiguo`` — perché ① da solo **sposta**
   il difetto invece di chiuderlo. Misurato subito dopo averlo scritto::

       prima di ①   «45.000» contro «45»  -> AMMESSO (confronto falso)
       dopo ① solo  «45.000» contro «45»  -> AMMESSO (nessun confronto)

   Per chi legge il fatto le due cose sono identiche. L'ha imposto ws8 smentendo
   la prima proposta: *«togliere l'accusa non distingue le due popolazioni: i
   falsi negativi nascono convertendo i veri positivi in silenzio»*. La regola,
   dal MEMORY.md: *«un avviso non ha bisogno della popolazione opposta, un veto
   sì»*. Il fatto entra, ma **smette di mentire sul proprio stato**.

Il criterio (9/9 su un banco di plausibilità, confermato sul corpus da ws8):
ambiguo = tre cifre dopo il punto, parte intera ≠ 0 e non più lunga di tre cifre.
Le due osservazioni che lo rendono preciso salvano dei decimali veri: ``0.250``
non può essere migliaia («zero mila duecentocinquanta» non esiste) e un gruppo di
migliaia ha ESATTAMENTE tre cifre, quindi ``3.1416`` è decimale certo.

COSTO DICHIARATO: ``3.141`` (pi greco) diventa non misurabile, ed è corretto — in
un testo italiano quel numero è tremilacentoquarantuno. Sul corpus di casa il
costo è zero: nelle righe lette da ws8 nessuna era un decimale legittimo.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from verimem.quantity_match import extract_quantities, numeri_ambigui
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

FONTE_45 = "Contratto: lo stipendio annuo e' 45 euro."


def test_IL_CUORE_il_valore_falso_non_viene_piu_prodotto():
    """Il difetto era qui: «45.000» valeva 45.0, e il gate lo confrontava."""
    assert extract_quantities("45.000 euro") == set()
    assert not valori_non_nella_fonte("Lo stipendio annuo e' 45.000 euro.", FONTE_45)


def test_IL_CUORE_ma_il_numero_NON_verificato_viene_DICHIARATO():
    """⚠️ LA META' CHE ws8 HA IMPOSTO. Senza questa, la cura sposta il difetto:
    il fatto entrerebbe lo stesso, e chi legge non saprebbe che quel numero non
    è stato confrontato con niente."""
    assert numeri_ambigui("Lo stipendio annuo e' 45.000 euro.") == ["45.000"]


def test_LA_PORTA_il_gate_emette_l_avviso_e_NON_quarantina(tmp_path, monkeypatch):
    """END-TO-END: è un AVVISO, non un veto. Il fatto entra — e lo dice."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    from verimem.client import Client

    r = Client().add("Lo stipendio annuo e' 45.000 euro.", topic="t", source=FONTE_45)
    layers = [w.get("layer") for w in (r.get("warnings") or [])]
    assert "L4.1-ambiguo" in layers, f"nessun avviso: {r.get('warnings')}"
    assert r.get("status") != "quarantined", "deve essere un avviso, non un veto"


def test_CONTROLLO_POSITIVO_un_fatto_senza_numeri_ambigui_non_riceve_rumore(
        tmp_path, monkeypatch):
    """⚠️ LA POPOLAZIONE OPPOSTA. Un avviso che compare sempre è rumore, e il
    rumore fa smettere di leggere proprio quando conta."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    from verimem.client import Client

    r = Client().add("Il magazzino contiene 480 pallet.", topic="t",
                     source="Inventario: il magazzino contiene 480 pallet.")
    layers = [w.get("layer") for w in (r.get("warnings") or [])]
    assert "L4.1-ambiguo" not in layers


def test_CONTROLLO_NEGATIVO_senza_separatore_il_layer_prende_ancora_tutto():
    """Il layer è SANO: il difetto stava in come veniva letto il numero, non nel
    confronto. Senza questo controllo il file sopra si leggerebbe come «abbiamo
    spento L4.1»."""
    assenti = valori_non_nella_fonte("Lo stipendio annuo e' 45000 euro.", FONTE_45)
    assert "45000" in [a.come_scritto() for a in assenti]


@pytest.mark.parametrize("testo", [
    "102.913 LOC",      # «OMNEX v6.3.0: 170 Python files, 102.913 LOC»
    "16.300 test",      # «16.300+ test pytest verdi» — in TRE fatti diversi
    "145.000 righe",
    "15.000 file",
])
def test_I_CASI_REALI_del_corpus_non_valgono_piu_un_millesimo(testo):
    """⚠️ NON sono casi inventati: sono righe del corpus di casa, trovate da ws8
    su `semantic.db` in sola lettura. Prima «16.300 test» valeva 16,3."""
    assert extract_quantities(testo) == set()
    assert numeri_ambigui(testo), f"«{testo}» deve essere DICHIARATO non misurabile"


@pytest.mark.parametrize("testo,valore", [
    ("0.250 s", 0.25),        # «zero mila duecentocinquanta» non esiste
    ("0.125 mm", 0.125),
    ("3.1416", 3.1416),       # quattro cifre: non è un gruppo di migliaia
    ("12.34 euro", 12.34),
    ("99.9 mb", 99.9),
    ("480 pallet", 480.0),
])
def test_I_DECIMALI_CERTI_sopravvivono(testo, valore):
    """⚠️ IL COSTO DELLA CURA, misurato invece che sperato: millesimi, tolleranze
    e precisione scientifica devono restare misurabili. Se cadono qui, la cura è
    troppo larga."""
    (_u, v), = extract_quantities(testo)
    assert v == pytest.approx(valore)
    assert not numeri_ambigui(testo)


def test_LA_CLASSE_INVISIBILE_resta_aperta_e_dichiarata():
    """📌 Il difetto gemello, NON curato e scritto qui perché non si perda: con
    due o più gruppi la regex non matcha affatto.

    Caso reale: «Il wheel torch 2.13.0 per Windows pesa 122.057.313 byte», un
    fatto salvato da ws8. È 50 volte più raro (2 su 9365 contro 100), e produce
    silenzio invece che una certificazione falsa — per questo viene dopo.
    ⚠️ Ma oggi non riceve nemmeno l'avviso: `numeri_ambigui` non lo vede, perché
    non lo vede la regex.
    """
    assert extract_quantities("Il wheel pesa 122.057.313 byte.") == set()
    assert numeri_ambigui("Il wheel pesa 122.057.313 byte.") == [], (
        "se un giorno questo diventa non-vuoto, la classe invisibile è stata "
        "curata: aggiorna il test e togli questa nota")
