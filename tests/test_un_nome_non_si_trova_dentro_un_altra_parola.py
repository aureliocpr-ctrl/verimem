"""«Rust» non e' dentro «trust», e «supported» non e' l'assenza di contraddizioni.

Reperto dell'altra istanza (in sola lettura), 2026-08-01, e il piu' grave della
sessione perche' e' il gate anti-confabulazione che confabula::

    "verimem e' scritto in Rust"                  -> unknown     conf=0.0
    "verimem e' scritto in Rust e usa Oracle DB"  -> supported   conf=0.5
         advice: «Claim coerente con la memoria.»

Aggiungere una SECONDA falsita' trasforma un onesto `unknown` in un `supported`.

LA CAUSA, misurata. I salienti della claim sono `['Database', 'Oracle',
'Rust']`, e uno dei fatti citati come evidenza ha `overlap = 0.667` (soglia
0.6)::

    «Su verimem la stessa claim sul database MySQL da verdetto contradicted
     senza topic_hint e unknown con topic_hint adhoc/trust-check, che era ...»
                                                          ^^^^

`_subj_overlap` fa `t.lower() in fact_lower`: cerca la SOTTOSTRINGA. «Rust» si
trova dentro «t·rust·-check», «database» c'e' davvero, «oracle» no — due su tre,
sopra soglia. Il fatto entra fra i candidati, non ha anni ne' quantita' in
conflitto, e finisce in `supporting`.

E' la classe gia' in memoria come feedback dopo sei falsi allarmi in una sola
sessione — «interroga la struttura, non il testo» — di cui il caso peggiore era
un test flaky per un `"91"` trovato dentro un id casuale. Qui la stessa cosa
decide se una claim e' verificata.

UNA CURA SOLA, ed e' quella minima: il CONFINE DI PAROLA. «Rust» dev'essere il
token «rust», non quattro lettere dentro un'altra parola. Non tocca nessuna
soglia e non cambia nessuna semantica — cambia solo cosa conta come presenza. Il
caso reale, misurato dopo: la claim allungata torna `unknown`.

CIO' CHE HO VISTO E NON HO CURATO, e va scritto perche' resta vero: `supported`
e' il ramo `else` di «non ho trovato una contraddizione». In linea di principio
un fatto che condivide abbastanza nomi e non contraddice nulla diventa evidenza
a favore, anche se non asserisce la claim. Col match su sottostringa quel ramo
si raggiungeva per sbaglio; col confine di parola serve un overlap di NOMI vero,
che e' molto piu' difficile da ottenere per caso.

Non l'ho cambiato di iniziativa: e' semantica del verdetto sul write path, e
poche ore fa ho gia' dovuto RITIRARE un rilevatore aggiunto senza che la
necessita' fosse dimostrata. Se emerge un caso reale in cui `supported` arriva
con overlap di nomi legittimo ma senza asserzione, quello e' il momento — e
questo file e' il posto dove aggiungerlo.

Il primo test e' il caso reale. Gli altri due sono le due meta' del contratto:
una claim che la memoria non ha mai visto e' `unknown`, e una che la memoria
sostiene davvero resta `supported` — altrimenti la cura sarebbe un mutismo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from verimem.validate_claim import _subj_overlap, validate_claim


@dataclass
class _F:
    id: str
    proposition: str
    topic: str = "project/verimem"
    confidence: float = 0.9
    verified_by: list = field(default_factory=list)
    source_episodes: list = field(default_factory=list)


class _Sem:
    def __init__(self, fatti): self._f = list(fatti)
    def search_facts(self, q, limit=20, **_kw): return list(self._f)
    def recall(self, q, k=5, **_kw): return [(f, 0.9) for f in self._f[:k]]


class _Ag:
    def __init__(self, fatti):
        self.semantic = _Sem(fatti)
        self.memory = None


def test_un_nome_non_si_trova_dentro_un_altra_parola():
    """Il cuore: «Rust» dentro «trust» valeva come presenza di «Rust»."""
    assert _subj_overlap({"Rust"}, "il default era adhoc/trust-check") == 0.0, (
        "«Rust» e' stato trovato dentro «trust»: il match e' su sottostringa, "
        "non su parola, e decide se una claim risulta verificata")
    assert _subj_overlap({"Rust"}, "il progetto e' scritto in Rust.") == 1.0
    assert _subj_overlap({"Rust"}, "IL PROGETTO USA rust OGGI") == 1.0, (
        "il confronto deve restare insensibile alle maiuscole: era gia' cosi' "
        "e serve per «Tonegawa» in claim contro «tonegawa» in memoria")


def test_una_claim_mai_vista_resta_unknown_anche_se_allunga():
    """Il caso reale dell'altra istanza, e la ragione per cui e' grave:
    ALLUNGARE una falsita' la faceva passare da `unknown` a `supported`."""
    a = _Ag([_F("f1", "Su verimem la stessa claim sul database MySQL da "
                      "verdetto contradicted senza topic_hint e unknown con "
                      "topic_hint adhoc/trust-check, che era il default")])
    r = validate_claim(a, "verimem e' scritto in Rust e usa Oracle Database",
                       threshold=0.6)
    assert r["verdict"] != "supported", (
        f"il gate anti-confabulazione dichiara sostenuta una claim che la "
        f"memoria non ha mai visto: {r}")


def test_una_claim_DAVVERO_sostenuta_resta_supported():
    """Controprova: una cura che rendesse tutto `unknown` passerebbe il test
    sopra e renderebbe il tool inutile.

    NOTA sul perche' la claim porta DUE nomi capitalizzati. La prima stesura
    scriveva «verimem» minuscolo, lasciando un solo saliente (`Python`), e
    riceveva `unknown` — ma quello NON e' il difetto: e' la regola dichiarata
    «servono >= 2 token salienti», deliberatamente conservativa perche' una
    claim con un solo nome proprio e' troppo generica per una verifica
    lessicale. Il test era sbagliato, non il prodotto."""
    a = _Ag([_F("f1", "Il progetto Verimem e' scritto in Python e usa SQLite "
                      "come database.")])
    r = validate_claim(a, "Il progetto Verimem e' scritto in Python.",
                       threshold=0.6)
    assert r["verdict"] == "supported", (
        f"un fatto che dice esattamente cio' che la claim afferma non la "
        f"sostiene piu': la cura ha reso il tool muto. {r}")
    assert "f1" in r["evidence_facts"], r
