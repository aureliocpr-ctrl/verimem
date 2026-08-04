"""Il prodotto sa che esiste un fatto nascosto su quel record, e non lo dice.

DUE DIFETTI CHE SI ERANO SEMPRE GUARDATI SEPARATI, e sono la stessa cosa vista
da due lati. Misurati il 04/08 fuori da pytest (sotto pytest l'embedder e' uno
stub su SHA-256 e ogni coseno e' finto):

① IL CATALOGO — 25 schede distinte, e ne resta UNA servibile::

       recall(«Quanto zinco contiene il campione S-007?»)
         -> «Il campione S-025 contiene zinco a 35 mg/l»   score 0.8786

   La risposta e' sbagliata, la confidenza e' alta, e S-007 sta nel database.
   Misurato su registri in tedesco, inglese, francese e spagnolo: 8 su 8.

② L'AGGIORNAMENTO QUARANTINATO — il gate blocca 5 aggiornamenti di stato veri
   su 12, e il vecchio stato resta vivo::

       [VIVO    ] model_claim   «Il ticket T-451 e' aperto...»
       [NASCOSTO] quarantined   «Il ticket e' stato chiuso il 3 marzo.»
       recall(«Il ticket T-451 e' ancora aperto?») -> «e' aperto»  0.8819

   ⚠️ La via d'uscita ESISTE: con `verified_by=['approval:C-12_signed']` nel
   formato che il detector dichiara, 4 fatti su 4 entrano. Il difetto non e'
   che il gate sia chiuso — e' che chi fa la domanda non sa che c'e' un
   aggiornamento fermo dietro la risposta che riceve.

LA CURA NON DECIDE, DICHIARA. Non cambia cosa si serve ne' come si ordina: dice
che su quel record esiste un fatto nascosto. E' l'unica mossa che non chiede di
distinguere un catalogo da un aggiornamento — otto criteri su otto sono caduti
provandoci, e la decima volta cadrebbe la nona.

⚠️ QUELLO CHE E' GIA' CADUTO, per non riprovarci:
  * l'ANCORAGGIO (codice o data nel testo) come segno di «fatto del mondo»:
    sul mio banco separava 6/6 contro 0/6, sul corpus vero **68% contro 66%**.
    Nel corpus reale anche le auto-dichiarazioni portano date e SHA.
  * il codice SENZA separatore: prendeva «M1» «B2» «P0» — i nomi delle regole —
    e dichiarava un codice nel 54% dei fatti. Col separatore obbligatorio: 18%.
"""
from __future__ import annotations

import pytest

from verimem.hidden_records import codes_in, hidden_records_for


class _Conn:
    """Le righe del database, senza il database: la funzione riceve una
    sequenza di (id, status, superseded_by, proposition)."""

    def __init__(self, righe):
        self.righe = righe

    def rows(self):
        return list(self.righe)


CATALOGO = [
    ("a1", "model_claim", None,
     "Il campione S-025 contiene zinco a 35 milligrammi per litro."),
    ("a2", "model_claim", "a1",
     "Il campione S-007 contiene zinco a 17 milligrammi per litro."),
]

QUARANTENA = [
    ("b1", "model_claim", None,
     "Il ticket T-451 e' aperto e assegnato al primo livello."),
    ("b2", "quarantined", None,
     "Il ticket T-451 e' stato chiuso il 3 marzo."),
]


def test_il_catalogo_dichiara_la_scheda_ritirata():
    """① La domanda nomina S-007, la risposta parla di S-025, e S-007 esiste
    ritirato: il prodotto deve dirlo."""
    out = hidden_records_for(
        _Conn(CATALOGO),
        query="Quanto zinco contiene il campione S-007?",
        served="Il campione S-025 contiene zinco a 35 milligrammi per litro.")
    assert out, "nessun record nascosto dichiarato per S-007"
    assert out[0]["code"] == "S-007"
    assert "S-007" in out[0]["text"]
    assert out[0]["why"] == "retired"


def test_l_aggiornamento_quarantinato_si_dichiara():
    """② Stesso record su entrambi i lati, ma dietro c'e' un aggiornamento
    fermo in quarantena. E' il caso che INVERTE la risposta."""
    out = hidden_records_for(
        _Conn(QUARANTENA),
        query="Il ticket T-451 e' ancora aperto?",
        served="Il ticket T-451 e' aperto e assegnato al primo livello.")
    assert out, "l'aggiornamento quarantinato non viene dichiarato"
    assert out[0]["code"] == "T-451"
    assert "chiuso" in out[0]["text"]
    assert out[0]["why"] == "quarantined"


def test_niente_da_dichiarare_quando_non_c_e_niente():
    """IL PRESIDIO PRINCIPALE. Se sul record non c'e' nessun fatto nascosto,
    la risposta esce identica a prima — che e' il caso di quasi ogni lettura."""
    righe = [("c1", "model_claim", None,
              "Il campione S-007 contiene zinco a 17 milligrammi per litro.")]
    out = hidden_records_for(
        _Conn(righe),
        query="Quanto zinco contiene il campione S-007?",
        served="Il campione S-007 contiene zinco a 17 milligrammi per litro.")
    assert out == []


def test_una_domanda_senza_codici_non_puo_far_scattare_niente():
    """L'ALTRO PRESIDIO: su prosa senza codici il lavoro e' zero — nessuna
    query, nessun campo. Sul corpus reale sono 4356 fatti su 5333."""
    out = hidden_records_for(
        _Conn(CATALOGO),
        query="Come va il progetto?",
        served="Il progetto procede secondo i tempi previsti.")
    assert out == []


@pytest.mark.parametrize("testo,attesi", [
    ("Il campione S-007 contiene zinco.", {"S-007"}),
    ("Il magazzino K-77 e la scheda REF-42.", {"K-77", "REF-42"}),
    ("Das Lager L-009 hat 163 Quadratmeter.", {"L-009"}),
])
def test_i_codici_di_record_si_riconoscono(testo, attesi):
    assert codes_in(testo) == attesi


@pytest.mark.parametrize("testo", [
    "La regola M1 e la regola B2 valgono sempre.",
    "Le priorita' P0 e P1 sono chiuse.",
    "Il modello QWEN2 gira su ROT3.",
])
def test_le_sigle_attaccate_al_numero_NON_sono_codici(testo):
    """SENZA QUESTO IL CRITERIO E' UNA BOMBA: senza separatore obbligatorio
    l'estrattore dichiarava un codice nel 54% dei fatti servibili del corpus
    (2891 su 5325) — e quei «codici» erano i nomi delle regole di casa."""
    assert codes_in(testo) == set()


def test_S_1_non_e_S_10(mono=None):
    """IL DIFETTO DEL LIKE, trovato confrontandolo con l'FTS sul corpus vero.

    ``WHERE proposition LIKE '%ROUND-1%'`` prende anche «ROUND-10»: su 60
    codici veri, LIKE e FTS davano risultati diversi in 15 casi, e questo era
    uno dei due versi. In un registro numerato S-1...S-100 cercare S-1 avrebbe
    restituito S-10, S-11 e S-100 come se fossero lo stesso record.

    Il filtro sul codice ESATTO e' cio' che lo impedisce, e per questo gira
    PRIMA del conteggio della soglia."""
    righe = [("v", "model_claim", None, "Il lotto S-10 pesa 40 chili."),
             ("w", "model_claim", None, "Il lotto S-100 pesa 55 chili."),
             ("x", "model_claim", "v", "Il lotto S-1 pesa 12 chili.")]
    out = hidden_records_for(_Conn(righe),
                             query="Quanto pesa il lotto S-1?",
                             served="Il lotto S-10 pesa 40 chili.")
    assert len(out) == 1, f"S-10 e S-100 non sono S-1: {out}"
    assert out[0]["text"] == "Il lotto S-1 pesa 12 chili."


def test_un_codice_che_nomina_troppi_fatti_e_un_ETICHETTA():
    """LA SOGLIA DI SELETTIVITA', e il corpus vero l'ha imposta.

    Senza, la dichiarazione arrivava a 2491 nascosti per UNA lettura: `TURN-0`
    compare in 1471 fatti e `REPORT-2026-05-28` in 1028. Quelli non
    identificano un record, identificano una categoria — e il taglio a 3 per
    codice limitava il volume e non la pertinenza."""
    etichetta = [(f"e{i}", "quarantined", None,
                  f"Nota numero {i} del TURN-0 di questa sessione.")
                 for i in range(12)]
    out = hidden_records_for(
        _Conn(etichetta),
        query="Cosa e' successo nel TURN-0?",
        served="Il turno si e' concluso senza incidenti.")
    assert out == [], f"un codice in 12 fatti va scartato: {out}"


def test_un_record_normalmente_rimisurato_resta_dichiarato():
    """IL PRESIDIO DELLA SOGLIA: dieci e' sopra il numero di rimisure che una
    scheda vera colleziona. Nove fatti sullo stesso codice restano visti."""
    righe = [(f"r{i}", "model_claim", "r9" if i < 9 else None,
              f"Il campione S-007 contiene zinco a {10 + i} milligrammi.")
             for i in range(9)]
    out = hidden_records_for(
        _Conn(righe),
        query="Quanto zinco contiene il campione S-007?",
        served="Il campione S-025 contiene rame a 40 milligrammi.")
    assert out, "nove fatti sullo stesso record devono restare dichiarabili"
    assert len(out) == 3, "e il taglio per codice resta 3"


@pytest.mark.parametrize("testo", [
    "Le password sono cifrate con SHA-256 dal 2024.",
    "The IL-6 levels were elevated in the treated cohort.",
    "COVID-19 vaccination reduced hospitalisation.",
    "Il protocollo HTTP/2 e' attivo su tutti gli endpoint.",
])
def test_i_nomi_di_cose_col_trattino_non_devono_far_danno(testo):
    """SHA-256, IL-6, COVID-19, HTTP/2 hanno la forma di un codice e NON sono
    identificativi di record. Il criterio li estrae — e non fa danno lo stesso,
    perche' dichiara solo se esiste un fatto NASCOSTO su quel codice. Misurato:
    zero falsi positivi su dieci enunciati di questo tipo."""
    out = hidden_records_for(
        _Conn([("z1", "model_claim", None, testo)]),
        query=testo, served=testo)
    assert out == []
