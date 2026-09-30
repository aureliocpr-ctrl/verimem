"""`00-ESAME.md` non afferma che qualcosa vale zero.

IL DIFETTO, misurato sullo store il 21/09 — quattro fatti VERI, col giudice fra
99,69 e 99,98, trattenuti perche' il numero del NOME DI UN DOCUMENTO non sta
nella fonte::

    4785000d96bf  g=99.69  «Il documento 03-cose-spente.md scrive che...»      accusa '03'
    1512d6b6ab2c  g=99.96  «Il documento 08-i-656-mb-le-quattro-strade.md...»  accusa '08'
    62c640210e41  g=99.86  «...docs/stato-reale/00-ESAME.md e arrivato a 22 celle...»  accusa '00'
    5980a16b0a9b  g=99.98  «Nel registro 00-ESAME.md dieci celle verdi...»     accusa '00'

E la PROVENIENZA e' provata, non somigliata: togliendo il nome di file dal claim
l'accusa SPARISCE (`[]` in tutti e quattro). E' il test che mancava al bersaglio
precedente di questo ticket, dove il valore «incluso» nel token veniva in realta'
da un'altra parte della frase — quel bersaglio e' stato ritirato.

⚠️ LA CURA STA NEL CONFRONTO, NON NEL PARSER. `extract_quantities` la usano sei
moduli del gate: insegnarle i nomi di file propagherebbe la conversione a tutti,
ed e' la stessa ragione gia' scritta in questo modulo per la notazione
scientifica. Qui si toglie una LETTURA dal confronto claim-fonte, non una
capacita' al parser — e l'ultima cella lo presidia.

RAGGIO, misurato sul corpus (18 285 fatti, snapshot in sola lettura): 134 letture
di `extract_quantities` cambiano (0,73%), di cui 10 su fatti trattenuti da
`L4.1`. La prima regex che avevo scritto ne cambiava 4845 perche' prendeva anche
«4/5» e «F#8/F#9»: qui l'esclusione e' legata alla SOLA estensione nota.
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import valori_non_nella_fonte

#: I quattro casi VERI dello store, con il loro id: non sono inventati per la
#: cura, sono le frasi che il prodotto ha trattenuto.
DALLO_STORE = [
    ("4785000d96bf",
     "Il documento 03-cose-spente.md scrive che nessuna riga del programma "
     "legge HIPPO_EXPOSE_TOOLS.",
     "Nel documento si legge che nessuna riga del programma legge "
     "HIPPO_EXPOSE_TOOLS."),
    ("1512d6b6ab2c",
     "Il documento 08-i-656-mb-le-quattro-strade.md scrive che il numero "
     "656 MB e' ESATTO.",
     "Il documento dichiara che il numero 656 MB e' ESATTO."),
    ("62c640210e41",
     "Il registro docs/stato-reale/00-ESAME.md e arrivato a 22 celle.",
     "Il registro e' arrivato a 22 celle."),
    ("5980a16b0a9b",
     "Nel registro 00-ESAME.md dieci celle verdi dichiarano una lingua diversa.",
     "Nel registro dieci celle verdi dichiarano una lingua diversa."),
]


@pytest.mark.parametrize("fact_id,claim,fonte",
                         DALLO_STORE, ids=[c[0] for c in DALLO_STORE])
def test_il_numero_del_nome_di_file_non_e_un_valore_assente(fact_id, claim, fonte):
    """IL RED: il numero del nome non e' una quantita' e non va accusato."""
    assenti = [v.come_scritto() for v in valori_non_nella_fonte(claim, fonte)]
    assert assenti == [], (
        f"il fatto {fact_id} e' trattenuto per il numero del NOME DI UN FILE: "
        f"{assenti} — il claim lo scrive come titolo, non come grandezza")


def test_ANCHE_i_numeri_INTERNI_al_nome_sono_esclusi():
    """La condizione che il lead ha aggiunto, e senza questa cella la cura
    sarebbe a meta': in `08-i-656-mb-le-quattro-strade.md` il numero **interno**
    `656` sta nel titolo quanto lo `08` iniziale, e con l'unita' attaccata
    («656-mb») verrebbe letto come una grandezza. L'esclusione copre il TOKEN
    INTERO, non solo la sua testa."""
    claim = "Il documento 08-i-656-mb-le-quattro-strade.md conferma la misura."
    assert [v.come_scritto() for v in valori_non_nella_fonte(
        claim, "Il documento conferma la misura.")] == [], (
        "un numero DENTRO il nome del file e' ancora letto come quantita'")


def test_IL_NEGATIVO_un_numero_vero_accanto_a_un_nome_resta_controllato():
    """LA POPOLAZIONE OPPOSTA. La cura toglie una lettura che non e' una misura;
    se togliesse anche le misure vere sarebbe un controllo spento, ed e' l'errore
    che questo modulo ha gia' pagato (riga 228: «i falsi negativi nascono
    convertendo i veri positivi in silenzio»)."""
    claim = "Il registro 00-ESAME.md e arrivato a 22 celle."
    assert [v.come_scritto() for v in valori_non_nella_fonte(
        claim, "Il registro e' arrivato a 30 celle.")] == ["22"], (
        "il numero VERO accanto al nome del file non viene piu' controllato")
    assert [v.come_scritto() for v in valori_non_nella_fonte(
        "Il commit 8a16bb90 ha 3 file.", "Il commit ha 5 file modificati.")] == ["3"], (
        "un numero vero accanto a un token esadecimale non viene piu' controllato")


def test_IL_CONTROLLO_POSITIVO_una_frase_senza_nomi_di_file_non_cambia():
    """Se la cura cambiasse anche le frasi che non contengono nomi di file, non
    starebbe escludendo i nomi: starebbe togliendo controlli a caso."""
    assert [v.come_scritto() for v in valori_non_nella_fonte(
        "Il contatore dei job puliti risulta 5 su 24.",
        "Il contatore dei job puliti risulta 7 su 24.")] == ["5"]


def test_IL_PERIMETRO_extract_quantities_resta_intatta():
    """⚠️ LA CELLA CHE TIENE LA CURA AL SUO POSTO. Il parser e' usato da sei
    moduli del gate: se un giorno qualcuno gli insegnasse i nomi di file, la
    conversione arriverebbe a tutti in silenzio. Questa cella asserisce il
    comportamento di OGGI del parser, difetto incluso — e diventa rossa il
    giorno che la cura si sposta di modulo, che e' il suo scopo."""
    from verimem.quantity_match import extract_quantities

    assert ("esame", 0.0) in extract_quantities(
        "Il registro docs/stato-reale/00-ESAME.md e arrivato a 22 celle."), (
        "il parser non legge piu' il nome del file come quantita': la cura si e' "
        "spostata dentro `extract_quantities` e tocca i sei moduli che la usano")


def test_LA_LISTA_DELLE_ESTENSIONI_STA_IN_UN_POSTO_SOLO():
    """La seconda condizione del lead: la cella LEGGE la lista dal modulo invece
    di ricopiarla. Una lista scritta due volte diverge — su questo prodotto e'
    gia' successo tre volte in due giorni con una soglia."""
    #: l'import sta QUI e non in testa al file di proposito: un `ImportError`
    #: a livello di modulo interrompe la RACCOLTA, e una raccolta che si ferma
    #: e' un campione, non un inventario — il RED delle altre celle sparirebbe.
    from verimem.valore_non_nella_fonte import ESTENSIONI_DI_FILE

    assert "md" in ESTENSIONI_DI_FILE and "py" in ESTENSIONI_DI_FILE
    for est in sorted(ESTENSIONI_DI_FILE):
        claim = f"Il file 07-prova.{est} conferma la misura."
        assert [v.come_scritto() for v in valori_non_nella_fonte(
            claim, "Il file conferma la misura.")] == [], (
            f"l'estensione {est!r} e' nella lista ma il numero del nome viene "
            "ancora accusato")
