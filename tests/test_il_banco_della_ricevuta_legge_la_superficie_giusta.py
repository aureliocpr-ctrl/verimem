"""Il banco che misura IL BANCO della ricevuta.

I sei test di `test_la_ricevuta_non_diceva_quale_cifra_mancava.py` sono rossi in
CI e verdi in locale. La causa non si leggeva, e non per mancanza di dati: il
banco leggeva l'output del CLI in due modi sbagliati, e ciascuno dei due
NASCONDE proprio l'informazione che serve a capire perche' e' rosso.

① NON GUARDAVA L'USCITA DEL PROCESSO. Un CLI che muore lascia un output tronco,
  e ogni assert riferisce allora «'L4.1' non c'e'» invece di «il processo e'
  morto». In CI il danno raddoppia: la piattaforma TRONCA le righe lunghe, i log
  strutturati riempiono il messaggio e la coda — dove starebbe la causa — viene
  tagliata prima di poter essere letta. E' cosi' che quel rosso e' rimasto senza
  causa per un giorno intero.

② LEGGEVA ANCHE I LOG STRUTTURATI, e li' dentro c'e' `layers=['L4.1']`. Quindi
  l'assert che pretende dalla RICEVUTA il nome del controllo che ha bocciato si
  accontentava di una RIGA DI LOG. Due superfici diverse, una sola stringa
  cercata: il banco poteva restare verde con la ricevuta muta. E' esattamente il
  difetto che quel file rimprovera al prodotto, ripetuto dentro il banco che lo
  misura — la dodicesima volta che ci capita, e la prima in cui il conto lo
  teniamo.

⚠️ PERCHE' IN UN FILE SEPARATO: il modulo curato porta un `pytestmark` che salta
tutto quando il giudice del moat non e' in cache. Questi due guardiani non
interrogano il giudice — misurano la lettura dell'output — e ereditando quel
marcatore tacerebbero proprio nella condizione in cui la lettura conta di piu'.
Un guardiano che si spegne insieme a cio' che sorveglia non e' un guardiano.

🔑 CRITERIO, quello di casa: «acceso = c'e' un test che diventa ROSSO se lo
spegni». Falsificati entrambi prima di consegnare, sostituendo la funzione con
l'identita' e ricontrollando che il guardiano se ne accorga.
"""
from __future__ import annotations

import pytest

from tests.test_la_ricevuta_non_diceva_quale_cifra_mancava import (
    leggi,
    solo_la_ricevuta,
)


def test_il_banco_dichiara_se_il_CLI_e_MORTO():
    """Il guardiano di ①."""
    grezzo = "2026-08-13T16:09:52.2 [info     ] flow.warmup phase=start"
    with pytest.raises(AssertionError) as e:
        leggi(-9, grezzo, "")
    m = str(e.value)
    # l'informazione decisiva PRIMA: se il messaggio viene tagliato si perde
    # la coda, non il verdetto
    assert m.startswith("CLI-MORTO exit=-9"), m
    # ⚠️ `len(grezzo)` e non la cifra scritta a mano: al primo giro l'avevo
    # contata a occhio e questo guardiano mi ha preso. Un numero copiato
    # invece che misurato e' cio' che l'intero fronte rimprovera al gate.
    assert f"len_stdout={len(grezzo)}" in m, m


def test_un_processo_riuscito_non_viene_dichiarato_morto():
    """⚠️ LA POPOLAZIONE OPPOSTA. Un presidio che allarma anche quando tutto e'
    andato bene non e' severo, e' rotto: si spegnerebbe alla prima settimana."""
    assert leggi(0, "quarantined id=abc topic=t", "") == "quarantined id=abc topic=t"
    assert leggi(0, None, "b") == "b"          # il caso None resta curato


def test_il_banco_legge_la_ricevuta_non_la_riga_di_log():
    """Il guardiano di ②."""
    con_log = ("2026-08-13T16:09:52.225778 [info     ] flow.write "
               "layers=['L4.1'] status=quarantined\n"
               "Loading weights: 100%|##########| 202/202 [00:00<00:00, 39it/s]\n"
               "quarantined id=abc topic=t\n"
               "  L4.1 — il claim afferma un valore che la fonte non contiene: 40")
    ripulito = leggi(0, con_log, "")
    # la riga di log se ne va...
    assert "status=quarantined" not in ripulito, ripulito
    assert "Loading weights" not in ripulito, ripulito
    # ...e la ricevuta resta INTERA, `L4.1` compreso: il filtro toglie la
    # superficie sbagliata, non l'informazione
    assert "quarantined id=abc" in ripulito
    assert "L4.1" in ripulito


def test_il_filtro_non_mangia_una_ricevuta_che_parla_di_orari():
    """🔎 IL CASO CHE POTREBBE ROMPERSI: il filtro riconosce una riga di log da
    un timestamp in testa. Una ricevuta che CONTENGA un orario non deve sparire
    — sarebbe un silenzio che nessuno noterebbe, perche' il test che lo
    scoprirebbe e' proprio quello che il filtro ha reso muto."""
    ricevuta = "quarantined id=abc — la fonte del 2026-08-13T10:00:00 non lo dice"
    assert solo_la_ricevuta(ricevuta) == ricevuta
