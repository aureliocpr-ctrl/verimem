"""README, gli strumenti che mutano gli episodi: la lista NON deve tornare.

STORIA, in un giorno solo (12/09/2026):

  ① il README stava per pubblicare «**the five** episode-mutating tools» con i
     cinque nomi — una lista CHIUSA, in prosa;
  ② @QA trova che ne manca almeno uno, e che quello omesso **cancella**;
  ③ misuro: 18 strumenti hanno `episode` nel nome, 22 metodi di EpisodicMemory
     scrivono, e **NESSUNA lista nel codice** dice quali mutano gli episodi ⇒ il
     numerale non era verificabile da nessuno, nemmeno da chi l'aveva scritto;
  ④ @Porte misura meglio e la riga esce **peggiore di come l'avevo accusata**:
     nominava **due strumenti che non scrivono niente** e ne **ometteva tre** che
     scrivono. Sbagliava nelle due direzioni insieme.
  ⑤ la cura che ha scritto e' migliore di quella che avevo proposto io: non
     toglie solo il numero, **dichiara perche' la lista non c'e'** —

     «The set is deliberately not enumerated here: a list in prose cannot be
      checked against the code, and the one that used to be here was wrong three
      ways at once.»

🔑 **QUESTO PRESIDIO GUARDA IL RITORNO, NON LA CURA.** Una lista in prosa e'
comoda da scrivere e sembra utile: fra un mese qualcuno la rimette, in buona fede,
con un numero nuovo. E il numero nuovo sara' sbagliato per la stessa ragione per
cui lo era quello vecchio — **non esiste nel codice l'oggetto che lo definisce**.

⚙️ Il test vale **prima e dopo** il merge della PR che porta la cura: cerca una
lista chiusa, non la frase nuova. Finche' non c'e' una lista, e' verde.

Presidio: Product Owner, 12/09/2026, sul README.
⚠️ **Non eseguito da chi lo ha scritto** (sola lettura). Atteso: **3 passed**.
"""

from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
README = RADICE / "README.md"

#: Un numerale (cifra o parola) che qualifica un insieme di strumenti.
_NUMERALE_DI_STRUMENTI = re.compile(
    r"\b(?:the\s+)?(?:two|three|four|five|six|seven|eight|nine|ten|\d{1,3})\s+"
    r"[a-z-]*\s*tools\b",
    re.I,
)
#: Un nome di strumento fra backtick. Una LISTA chiusa e' un numerale CHE ELENCA:
#: il numerale da solo non basta.
_NOME_DI_STRUMENTO = re.compile(r"`hippo_[a-z_0-9]+`")
#: Quanto vicino deve stare l'elenco al numerale perche' sia LA SUA lista.
_VICINANZA = 220

# ⚠️ PERCHE' SERVE LA VICINANZA, e l'ho scoperto su questo stesso test.
# Il primo criterio era «numerale + tools», e sul README curato trovava
# «it named TWO TOOLS that write nothing» — che e' la frase con cui il documento
# RACCONTA il difetto, non una lista che lo commette. Un pattern sulla forma
# prende anche chi descrive l'errore invece di chi lo fa.
# ⇒ Una lista chiusa e' un numerale CON DEI NOMI ACCANTO.

#: Le parole con cui il README dichiara di NON enumerare. Se ci sono, la scelta
#: e' esplicita ed e' quella giusta.
_DICHIARA_DI_NON_ELENCARE = re.compile(r"deliberately not enumerated", re.I)


def _testo() -> str:
    assert README.is_file(), f"il README non e' al suo posto: {README}"
    return README.read_text(encoding="utf-8", errors="replace")


def _liste_chiuse(testo: str) -> list[str]:
    """Un numerale di strumenti che ne ELENCA almeno due, li' accanto."""
    fuori = []
    for m in _NUMERALE_DI_STRUMENTI.finditer(testo):
        intorno = testo[m.start() : m.end() + _VICINANZA]
        if len(_NOME_DI_STRUMENTO.findall(intorno)) >= 2:
            fuori.append(m.group(0))
    return fuori


def test_il_readme_non_chiude_un_insieme_di_strumenti_con_un_numerale():
    testo = _testo()
    chiusure = _liste_chiuse(testo)
    assert not chiusure, (
        f"il README chiude un insieme di strumenti con un numerale: {chiusure}. "
        "Il 12/09 una riga cosi' («the five episode-mutating tools») nominava due "
        "strumenti che non scrivono niente e ne ometteva tre che scrivono — e "
        "nessun criterio nel codice poteva chiuderla. Un numero in prosa su una "
        "famiglia di strumenti **non e' verificabile**: o esiste nel prodotto la "
        "costante che la definisce e il README la cita, oppure la lista non si "
        "scrive."
    )


def test_se_il_readme_parla_di_quell_insieme_dichiara_di_non_elencarlo():
    """La meta' POSITIVA: quando la frase c'e', deve dire perche' non elenca.

    Prima del merge della cura la frase non c'e' ancora e questo test e' verde
    per assenza — e **lo dice**, invece di far credere che il presidio stia
    misurando qualcosa.
    """
    testo = _testo()
    parla = "tools that mutate episodes" in testo
    if not parla:
        print(  # noqa: T201
            "\n[nota] il README non contiene ancora la frase sugli strumenti che "
            "mutano gli episodi: questo test e' verde per ASSENZA. Tornera' a "
            "misurare quando la cura entra in main."
        )
        return
    assert _DICHIARA_DI_NON_ELENCARE.search(testo), (
        "il README parla degli strumenti che mutano gli episodi ma non dichiara "
        "piu' di non elencarli: se e' tornata una lista, vedi l'altro test; se la "
        "dichiarazione e' stata solo riformulata, aggiorna questo presidio."
    )


# ── IL CONTROLLO POSITIVO DEL RIGHELLO ──────────────────────────
#
# Un presidio che cerca l'ASSENZA di qualcosa passa anche quando ha smesso di
# saper cercare. Questi due casi lo tengono onesto: il primo e' la riga com'era
# PRIMA della cura (deve accendersi), il secondo e' la frase con cui il README
# oggi RACCONTA quel difetto (non deve accendersi — e' il falso positivo che
# questo test aveva davvero, prima di chiedere i nomi accanto al numerale).

_RIGA_COM_ERA = (
    "Episodes stay local by design, so the five episode-mutating tools "
    "(`hippo_episode_pin`, `hippo_episode_unpin`, `hippo_rollup_old_episodes`, "
    "`hippo_episodes_dedup`, `hippo_episode_classify`) act on the session's own store"
)
_RIGA_CHE_RACCONTA = (
    "the one that used to be here was wrong three ways at once - it named two "
    "tools that write nothing, missed three that do, and no criterion could close it"
)


def test_CONTROLLO_il_righello_accende_sulla_riga_vecchia_e_tace_sul_racconto():
    assert _liste_chiuse(_RIGA_COM_ERA), (
        "il righello non riconosce piu' la lista chiusa che ha motivato questo "
        "presidio: da qui in poi il verde dell'altro test non vuol dire niente."
    )
    assert not _liste_chiuse(_RIGA_CHE_RACCONTA), (
        "il righello si accende sulla frase che RACCONTA il difetto invece che su "
        "una lista che lo commette: e' il falso positivo di partenza, un numerale "
        "senza nomi accanto non e' una lista."
    )
