"""Il cancello dei messaggi leggeva i commenti PRIMA che esistessero.

🔴 MISURATO IL 18/09/2026, su cinque richieste, e l'esito dipendeva SOLO
dall'ordine fra due istanti — non dal contenuto:

    PR   esito  run vincente          commento con la DoD    ordine
    #65  ok     17/09 19:30:47Z       16/09 19:06:59Z        commento 24 h prima
    #66  ok     18/09 17:18:53Z       17/09 18:38:08Z        commento 23 h prima
    #68  ROSSO  18/09 17:16:22Z       18/09 17:16:49Z        run 27 s prima
    #69  ROSSO  18/09 17:21:10Z       18/09 17:21:34Z        run 24 s prima
    #71  ROSSO  18/09 17:25:26Z       18/09 17:25:52Z        run 26 s prima

Le due verdi non erano migliori: erano VECCHIE, e il loro run vincente era
arrivato un giorno dopo il commento. Le tre rosse erano le tre richieste aperte
quel giorno nel flusso normale — quello che `CONTRIBUTING.md` prescrive.

⇒ Nessuno puo' aprire una richiesta e commentarla nello stesso istante: il
cancello leggeva i commenti nell'UNICO momento in cui e' garantito che non ce ne
siano, e `on:` non ha `issue_comment`, quindi non si ripeteva mai da se'.

🪞 E la lezione era gia' scritta il giorno prima — «l'oggetto che nasce DOPO
l'ultimo controllo». Non era una regola mancante: era una regola non applicata.

⚠️⚠️ LA COSA PEGGIORE NON ERA IL ROSSO, ERA LA DIAGNOSI. Il cancello scriveva
«nessun commento porta la DoD» mentre il commento c'era: chi leggeva concludeva
di aver sbagliato e riscriveva una cosa giusta. Un messaggio che MENTE su cio'
che vede costa piu' di un rosso muto, e i due test qui sotto presidiano le due
meta' della cura — l'attesa e la franchezza.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "scripts"))

import messaggio_pulito as mp  # noqa: E402

WORKFLOW = RADICE / ".github" / "workflows" / "messaggi.yml"


def _passo_che_legge_i_commenti(testo: str) -> str:
    """Il passo del workflow che interroga i commenti della richiesta.

    ⚠️ Si taglia sull'INIZIO RIGA di un `- name:` allo stesso rientro, non su
    una sottostringa: tagliare su una sottostringa ha gia' decapitato un file
    in questo repository, e un passo tagliato a meta' fa passare il test per
    la ragione sbagliata.
    """
    inizi = [m.start() for m in re.finditer(r"^      - name: ", testo, re.M)]
    for inizio, fine in zip(inizi, inizi[1:] + [len(testo)], strict=True):
        passo = testo[inizio:fine]
        if "/comments" in passo:
            return passo
    raise AssertionError(
        "nessun passo del workflow interroga i commenti della richiesta: "
        "o il cancello non li guarda piu', o questo test cerca la cosa "
        "sbagliata — in entrambi i casi il presidio va riscritto, non tolto"
    )


def test_la_lettura_dei_commenti_ritenta():
    """Il cancello deve ATTENDERE il commento, non fotografare l'istante zero.

    I tre casi misurati stavano fra 24 e 27 secondi: un cancello che guarda una
    volta sola perde il 100% delle richieste aperte nel modo prescritto.
    """
    passo = _passo_che_legge_i_commenti(WORKFLOW.read_text(encoding="utf-8"))
    assert "sleep" in passo, (
        "il passo legge i commenti UNA VOLTA SOLA, senza mai attendere: "
        "il commento con la DoD nasce ~25 s dopo che il job e' partito "
        "(misurato su #68, #69, #71 il 18/09), quindi non c'e' ancora"
    )


def test_quando_manca_la_dod_il_messaggio_dice_QUANDO_ha_guardato():
    """La diagnosi deve portare il suo istante e la via d'uscita.

    Finche' il controllo e' una gara, puo' perderla; quando la perde deve dire
    che ha guardato in un momento, non che la richiesta e' sbagliata.
    """
    problemi = mp.controlla_corpo("Una.\n", commenti=["un commento qualunque"])
    assert problemi, "il caso senza DoD deve restare un problema: la cura non e' un condono"
    diagnosi = "\n".join(problemi)

    assert re.search(r"al momento di questo controllo|quando questo controllo",
                     diagnosi, re.I), (
        "la diagnosi afferma un'ASSENZA senza dire quando ha guardato: "
        f"chi la legge crede di aver sbagliato. Diagnosi: {diagnosi!r}"
    )
    assert "rerun" in diagnosi, (
        "la diagnosi non dice come rilanciare il controllo: un rosso senza "
        f"via d'uscita ferma chi ha gia' fatto la cosa giusta. Diagnosi: {diagnosi!r}"
    )
