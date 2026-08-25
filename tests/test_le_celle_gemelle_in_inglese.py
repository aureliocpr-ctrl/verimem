"""Le stesse celle del presidio entita'/supersessione, dette in INGLESE.

PERCHE' QUESTO FILE ESISTE. I banchi che proteggono la supersessione sono scritti
in italiano — tutti. `test_il_fatto_di_bruno_archiviava_quello_di_anna.py` ha sei
celle e sei sono italiane; il gemello sul grafo delle entita' pure. E' naturale:
le scriviamo noi, e noi scriviamo in italiano.

Il costo di quella naturalezza, misurato il 2026-08-25: **un difetto che colpisce
solo l'inglese non ha modo di diventare rosso.** Non «e' difficile da vedere»:
non ha una superficie su cui manifestarsi. Aggiungendo le sei celle gemelle qui
sotto, DUE sono nate rosse nel primo minuto — e una delle due nessuno l'aveva
mai vista, perche' nessuno aveva mai posto la domanda in inglese.

⚖️ PORTATA, dichiarata subito perche' non sembri piu' grande di quello che e':
sul corpus di casa (11943 fatti vivi) le frasi prevalentemente inglesi sono 292,
il 2,4%, e i fatti con un nome proprio attributivo perso sono QUATTRO — tutti e
quattro referti scritti mentre si misurava questo difetto. **Sul corpus di casa
la portata e' zero.** Il dogfooding non esercita l'inglese, ed e' esattamente il
motivo per cui il difetto e' sopravvissuto: il corpus di casa non e' il corpus di
un utente inglese, e il prodotto promette «memory for AI agents», non «for
English agents» (RELEASE_GATE, G10, aperto dal 2026-07-04).

🔑 I DUE ROSSI SONO `xfail(strict=True)`, NON commentati e NON addomesticati a
`False`. Scriverli `False` significherebbe registrare il difetto come il
comportamento giusto — una decorazione, non un presidio. `strict=True` e' la
forma che avvisa in ENTRAMBE le direzioni: oggi documenta un difetto reale,
domani diventa rosso da solo nel momento in cui qualcuno lo cura e si dimentica
di togliere il marcatore. Con `strict=False` sarebbe un sensore scollegato.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import _entita_diverse

# ------------------------------------------------------------------ le gemelle
# Ogni cella e' la traduzione fedele di una riga di
# `test_il_fatto_di_bruno_archiviava_quello_di_anna.py::test_l_asse_e_l_entita_non_l_autore`.
# L'atteso NON e' stato scelto qui: e' quello della cella italiana. Una gemella
# che si sceglie da sola l'atteso non misura la parita', la simula.

@pytest.mark.parametrize("a,b,diverse", [
    # 1 — codice E citta' su entrambi i lati: due magazzini diversi
    ("Warehouse K-77 in Rovigo has 4200 square metres.",
     "Warehouse Z-08 in Ancona has 2600 square metres.", True),
    # 2 — stesso codice, valore nuovo: e' un aggiornamento, si archivia
    ("Patient P-9 weighs 70 kilograms.",
     "Patient P-9 weighs 78 kilograms.", False),
    # 3 — codice su un lato solo: «non so» non autorizza il ritiro
    ("Warehouse K-77 has 4200 square metres.",
     "The Ancona warehouse has 2600 square metres.", True),
    # 4 — stessa entita', valore nuovo: si archivia
    ("Patient Rossi weighs 70 kilograms.",
     "Patient Rossi weighs 78 kilograms.", False),
])
def test_le_celle_che_reggono_anche_in_inglese(a, b, diverse):
    """Le quattro celle in cui la parita' IT/EN c'e' gia'.

    Servono qui come CONTROLLO POSITIVO delle due che seguono: senza di loro,
    due xfail isolati si leggerebbero come «l'inglese non funziona», che e'
    falso e sarebbe un allarme peggiore del difetto."""
    assert _entita_diverse(b, a) is diverse


@pytest.mark.xfail(strict=True, reason=(
    "2026-08-25: in inglese DUE PERSONE DIVERSE non risultano diverse, e in "
    "italiano si'. Misurato a variabile singola, cambia solo la lingua:\n"
    "    IT «Il paziente Rossi ...» / «Il paziente Bianchi ...» -> True\n"
    "    EN «Patient Rossi ...»     / «Patient Bianchi ...»     -> False\n"
    "E NON e' la stessa causa dell'altro xfail qui sotto: li' l'estrattore non "
    "vede il nome, qui lo vede e la guardia lo ignora lo stesso —\n"
    "    extract_entities_lite('Patient Rossi weighs 70 kilograms.')   -> ['Patient Rossi']\n"
    "    extract_entities_lite('Patient Bianchi weighs 95 kilograms.') -> ['Patient Bianchi']\n"
    "Due entita' DISTINTE, e `_entita_diverse` risponde False. In italiano le "
    "stesse due frasi danno ['Rossi'] e ['Bianchi'] e la guardia risponde True: "
    "la differenza e' che in inglese il nome comune resta INCOLLATO al proprio.\n"
    "⚠️ Questo e' registrato come MISURA, non come diagnosi: il punto esatto in "
    "cui la coppia viene scartata non e' stato isolato, e chi lo curera' deve "
    "trovarlo, non fidarsi di questa riga.\n"
    "⛔ Il caso e' un referto medico: il fatto che sparisce e' il peso di un "
    "paziente sostituito da quello di un altro paziente."))
@pytest.mark.parametrize("a,b,diverse", [
    ("Patient Rossi weighs 70 kilograms.",
     "Patient Bianchi weighs 95 kilograms.", True),
])
def test_due_persone_diverse_in_inglese(a, b, diverse):
    assert _entita_diverse(b, a) is diverse


@pytest.mark.xfail(strict=True, reason=(
    "2026-08-25: il nome proprio in posizione ATTRIBUTIVA — «The Rovigo "
    "warehouse», la forma piu' comune dell'inglese — non viene estratto, quindi "
    "due magazzini diversi risultano la stessa cosa e uno archivia l'altro.\n"
    "CATENA, a variabile singola con controllo positivo su ogni riga:\n"
    "    extract_entities_lite('The Rovigo warehouse has 4200 square metres.')\n"
    "        -> []                     <- il nome sparisce\n"
    "    extract_entities_lite('The warehouse in Rovigo has 4200 square metres.')\n"
    "        -> [('Rovigo','place')]   <- stessa frase, nome dopo la preposizione\n"
    "⇒ `_proper` riceve due insiemi vuoti ⇒ `_entita_diverse` risponde False ⇒ "
    "`same-source evolution` archivia. Alla porta, store pulito, quattro "
    "scritture: «The Rovigo warehouse has 4200 square metres» risulta "
    "ARCHIVIATO da «The Trento warehouse has 1800 square metres», mentre le due "
    "frasi italiane corrispondenti restano ENTRAMBE vive.\n"
    "⇒ Il danno non e' un rifiuto — quello si vede — ma una CANCELLAZIONE "
    "SILENZIOSA di un fatto vero.\n"
    "TAGLIA della cecita', 8 frasi con il proprio controllo positivo: il nome "
    "attributivo e' perso in 8 casi su 8 (Rovigo, Frankfurt, Stripe, Ancona, "
    "Boeing, Dublin, Rossi, Milan). In DUE la perdita e' MASCHERATA da un'altra "
    "entita' nella lista ('The Dublin office closed in March' -> ['March']): "
    "quelli sono i casi peggiori, perche' un controllo del tipo «l'estrattore "
    "ha trovato qualcosa?» li legge come riusciti.\n"
    "⛔ La cura NON e' allargare il regex ai nomi attributivi senza misurare: "
    "renderebbe entita' anche «The Monday meeting» e «The Python script», e i "
    "falsi positivi vanno contati prima. `extract_entities_lite` ha un owner."))
@pytest.mark.parametrize("a,b,diverse", [
    ("The Rovigo warehouse has 4200 square metres.",
     "The Trento warehouse has 1800 square metres.", True),
])
def test_due_magazzini_diversi_in_inglese(a, b, diverse):
    assert _entita_diverse(b, a) is diverse


# ------------------------------------------ le gemelle del secondo presidio
# Da `test_la_cella_sei_si_chiude_col_grafo_delle_entita.py::
# test_il_grafo_distingue_dove_i_codici_non_arrivavano`. Stesso metodo: l'atteso
# viene dalla cella italiana.

@pytest.mark.parametrize("a,b,diverse", [
    # stesso magazzino, valore nuovo: e' un aggiornamento
    ("Warehouse K-77 in Rovigo has 4200 square metres.",
     "Warehouse K-77 in Rovigo has 5100 square metres.", False),
    # stesso server, valore nuovo
    ("The production server has 64 GB of RAM.",
     "The production server has 128 GB of RAM.", False),
    # soggetto implicito su un lato: «non so» non autorizza il ritiro
    ("Patient Rossi weighs 70 kilograms.",
     "The recorded weight is 95 kilograms.", True),
])
def test_le_celle_del_grafo_che_reggono_in_inglese(a, b, diverse):
    assert _entita_diverse(b, a) is diverse


@pytest.mark.xfail(strict=True, reason=(
    "2026-08-25: due DATACENTER con codici diversi non risultano diversi in "
    "inglese, e in italiano si'. Cambia solo la lingua:\n"
    "    IT «Il datacenter DC-Nord ...» / «Il datacenter DC-Sud ...»   -> True\n"
    "    EN «Data center DC-North ...»  / «Data center DC-South ...»   -> False\n"
    "🔑 E QUI L'ESTRATTORE NON C'ENTRA — e' il terzo caso e la terza volta che la "
    "causa e' diversa da quella che sembrava. Vede le STESSE entita' nelle due "
    "lingue:\n"
    "    IT -> ['DC', 'Nord']  /  ['DC', 'Sud']\n"
    "    EN -> ['DC', 'North'] /  ['DC', 'South']\n"
    "Quattro insiemi popolati e distinti a due a due, e la guardia risponde True "
    "in italiano e False in inglese. `DC` cade da entrambe le parti perche' "
    "`_proper` esclude gli acronimi di proposito (un acronimo e' un TIPO, non "
    "un'istanza), quindi la decisione resta a Nord/Sud contro North/South: due "
    "coppie simmetriche, due esiti opposti.\n"
    "⚠️ MISURA, NON DIAGNOSI. Non ho isolato dove le due coppie divergono e non "
    "lo suggerisco: la spiegazione ovvia («North e South saranno in una "
    "stoplist») e' una congettura che non ho verificato, e in questo file ce ne "
    "sono gia' due morte allo stesso modo.\n"
    "⛔ Il caso e' un inventario di infrastruttura: 480 rack di un datacenter "
    "sostituiti dai 512 di un ALTRO datacenter."))
@pytest.mark.parametrize("a,b,diverse", [
    ("Data center DC-North has 480 racks installed.",
     "Data center DC-South has 512 racks installed.", True),
])
def test_due_datacenter_diversi_in_inglese(a, b, diverse):
    assert _entita_diverse(b, a) is diverse


def test_la_parita_si_misura_sulle_STESSE_frasi():
    """La guardia di questo file, ed e' la cosa che lo tiene onesto.

    Una gemella tradotta male non misura la lingua: misura la traduzione. Qui
    si verifica che sulle coppie ITALIANE originali la funzione dia ancora gli
    stessi valori — se un giorno cambiassero, le celle inglesi qui sopra
    starebbero misurando un altro fenomeno e i loro `xfail` andrebbero riletti
    da capo, non aggiornati."""
    assert _entita_diverse("Il paziente Bianchi pesa 95 chilogrammi.",
                           "Il paziente Rossi pesa 70 chilogrammi.") is True
    assert _entita_diverse("Il magazzino di Trento ha 1800 metri quadrati.",
                           "Il magazzino di Rovigo ha 4200 metri quadrati.") is True
    # e il verso che DEVE archiviare, in entrambe le lingue
    assert _entita_diverse("Il paziente Rossi pesa 78 chilogrammi.",
                           "Il paziente Rossi pesa 70 chilogrammi.") is False
    assert _entita_diverse("Patient Rossi weighs 78 kilograms.",
                           "Patient Rossi weighs 70 kilograms.") is False
