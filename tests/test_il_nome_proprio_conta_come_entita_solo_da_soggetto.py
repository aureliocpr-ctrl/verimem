"""T14 — un nome proprio nel VALORE non è un'entità diversa.

VIA del CTO (06/09 00:52), causa accettata dopo quattro bracci eseguiti: il gate
trova la contraddizione e la classifica `L3-coexistence` perché
`_entita_diverse` guarda i nomi propri **ovunque stiano**. Quando il nome
proprio è il valore che cambia — «il fornitore del checkout è *Stripe*» → «…è
*Adyen*» — lo scambia per un soggetto diverso, e due valori dello stesso
attributo restano vivi insieme.

TERZO ASSE DELLA STESSA FORMA. Il docstring di `_entita_diverse` racconta i
primi due: l'AUTORE (ritirato — «autori diversi» non implica «cose diverse») e
l'ENTITÀ (la cura attuale). Questo è il VALORE. Il commento a
`anti_confab_gate:2112` dice la stessa cosa con altre parole: *«il messaggio
scambiava l'entità nominata DENTRO il fatto con l'autore DEL fatto»*.

LO STATO DI PARTENZA, misurato prima di scrivere una riga di cura::

    COESISTONO   DC-Nord/DC-Sud    diverse=True   A=['Nord']   B=['Sud']      ✓
    COESISTONO   Rossi/Bianchi     diverse=True   A=['Rossi']  B=['Bianchi']  ✓
    AGGIORNA     64GB/128GB        diverse=False  A=[]         B=[]           ✓
    AGGIORNA     Stripe/Adyen      diverse=True   A=['Stripe'] B=['Adyen']    ✗
    AGGIORNA     Rossi 70→78       diverse=False  A=['Rossi']  B=['Rossi']    ✓

⇒ **Quattro casi su cinque sono già giusti.** Il difetto è isolato al caso in
cui il proper sta nel PREDICATO, e la differenza strutturale si vede a occhio:
nei casi corretti il nome proprio è il SOGGETTO («Il paziente *Rossi*», «Il
datacenter *DC-Nord*»), in quello sbagliato è ciò che il soggetto VALE.

⚠️ LA POPOLAZIONE PROTETTA NON È NEGOZIABILE (condizione del CTO): le
coesistenze vere restano identiche cella per cella. Un criterio che le muove è
una regressione, non una cura — ed è già successo: il docstring porta la
tabella di quando la cura sull'asse dell'autore fece tornare vivi entrambi i
fatti in «due autori, aggiornamento», il caso più comune che esista.

⚠️ E SEI CRITERI LESSICALI SONO GIÀ CADUTI su questa funzione (i nomi propri
via `_CAPS_RE`, l'ancoraggio, l'allargamento di `codes_in` alla coda
alfabetica). Questo file non propone il settimo: FISSA IL CONTRATTO — chi è
aggiornamento e chi coesistenza — e lascia al codice il come. Se la cura passa
questi casi e non muove i protetti, regge; se ne muove uno, non regge.

PREDIZIONI DEPOSITATE PRIMA (06/09 01:00):
  P1 — i protetti (coesistenze vere) sono VERDI ora e devono restare verdi.
  P2 — «Stripe → Adyen» è ROSSO ora: è il RED di T14.
  P3 — gli aggiornamenti già riconosciuti (64GB→128GB, Rossi 70→78) sono VERDI
       ora e devono restare verdi: sono il controllo che la cura non allarga
       troppo dall'altra parte.

⚠️ NESSUN GIUDICE: `_entita_diverse` è pura e legge solo le due proposizioni.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from verimem.anti_confab_gate import _entita_diverse  # noqa: E402
from verimem.semantic import Fact  # noqa: E402


def _f(prop: str) -> Fact:
    return Fact(proposition=prop, topic="t14")


#: (etichetta, vecchio, nuovo). Il nome proprio è il SOGGETTO: due record.
PROTETTI_COESISTENZA = [
    ("due datacenter",
     "Il datacenter DC-Nord ospita il database.",
     "Il datacenter DC-Sud ospita il database."),
    ("due pazienti",
     "Il paziente Rossi pesa 70 chilogrammi.",
     "Il paziente Bianchi pesa 78 chilogrammi."),
    ("due progetti",
     "Il progetto Aurora scade a marzo.",
     "Il progetto Boreale scade ad aprile."),
]

#: ⚠️ IL PRESIDIO DELL'ORDINE. Il via del CTO diceva «PRIMA il soggetto»; qui
#: il soggetto è lo STESSO su entrambi (`subject_of` → 'server') e i due fatti
#: sono comunque DUE MACCHINE, perché a separarle è un IDENTIFICATORE. Se la
#: cura mettesse il soggetto prima dei codici, questo caso diventerebbe un
#: aggiornamento e una delle due macchine sparirebbe dalla memoria.
#: Misurato prima di scrivere la cura: `codes_in` le separa già, `_entita_diverse`
#: dice True. L'ordine giusto è: identificatori → soggetto → nomi propri.
PROTETTI_IDENTIFICATORE = [
    ("due server con codice",
     "Il server e' SRV-01.",
     "Il server e' SRV-02."),
]

#: Il soggetto è lo stesso e cambia il VALORE dello stesso attributo.
AGGIORNAMENTI = [
    ("la memoria del server (nessun proper)",
     "Il server ha 64 GB di RAM.",
     "Il server ha 128 GB di RAM."),
    ("il peso dello stesso paziente",
     "Il paziente Rossi pesa 70 chilogrammi.",
     "Il paziente Rossi pesa 78 chilogrammi."),
    ("IL CASO DI T14: il fornitore cambia",
     "Il fornitore di pagamenti del servizio checkout e' Stripe.",
     "Il fornitore di pagamenti del servizio checkout e' Adyen."),
]


@pytest.mark.parametrize("nome,vecchio,nuovo", PROTETTI_COESISTENZA,
                         ids=[c[0] for c in PROTETTI_COESISTENZA])
def test_P1_le_coesistenze_vere_restano_coesistenze(nome, vecchio, nuovo):
    """La popolazione protetta. Verde ora, verde dopo la cura, cella per cella."""
    assert _entita_diverse(_f(nuovo), _f(vecchio)) is True, (
        f"«{nome}»: due record distinti sono diventati un aggiornamento. La cura "
        "ha allargato dalla parte sbagliata e uno dei due fatti verra' ritirato")


@pytest.mark.parametrize("nome,vecchio,nuovo", AGGIORNAMENTI,
                         ids=[c[0] for c in AGGIORNAMENTI])
def test_P2_P3_un_valore_che_cambia_e_un_aggiornamento(nome, vecchio, nuovo):
    """Stesso soggetto, stesso attributo, valore diverso: NON sono due entita'.

    I primi due casi sono gia' verdi e stanno qui come controllo: se la cura li
    rompesse, avrebbe stretto invece di correggere. Il terzo e' il RED di T14.
    """
    assert _entita_diverse(_f(nuovo), _f(vecchio)) is False, (
        f"«{nome}»: il criterio legge il VALORE come un soggetto diverso, quindi "
        "i due fatti coesistono e la memoria serve insieme il dato vecchio e "
        "quello nuovo senza dire quale vale")


@pytest.mark.parametrize("nome,vecchio,nuovo", PROTETTI_IDENTIFICATORE,
                         ids=[c[0] for c in PROTETTI_IDENTIFICATORE])
def test_P4_un_identificatore_batte_il_soggetto_uguale(nome, vecchio, nuovo):
    """L'ordine dei rami, reso rosso se qualcuno lo inverte.

    Il soggetto è lo stesso ('server') e i due fatti restano DUE RECORD: a
    separarli è il codice. Questo test cade se la cura del soggetto viene
    spostata PRIMA degli identificatori — che è esattamente la forma in cui il
    via era stato scritto, e la ragione per cui l'ho misurata invece di
    applicarla alla lettera.
    """
    assert _entita_diverse(_f(nuovo), _f(vecchio)) is True, (
        f"«{nome}»: due macchine con codici diversi sono diventate un "
        "aggiornamento. Il ramo del soggetto e' stato messo PRIMA degli "
        "identificatori e una delle due sparisce dalla memoria")
