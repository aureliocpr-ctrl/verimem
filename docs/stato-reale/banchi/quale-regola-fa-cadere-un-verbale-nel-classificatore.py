"""QUALE DELLE CINQUE REGOLE FA CADERE UN VERBALE — la diagnosi, non il verdetto.

`W7-60` aveva misurato che sui verbali d'ufficio il classificatore del soggetto
dice **0 su 8**, e ne aveva concluso che *«la causa e' il CLASSIFICATORE, e il
percorso non e' nemmeno raggiunto»*. **Vero ma grosso**: non diceva **perche'**.
`W7-71` ha poi visto la stessa carve-out **funzionare** su materiale tecnico
(3 casi su 24 salvati con `L1-domain-precision-observe`).

⇒ **Due misure mie che divergono, e la spiegazione non l'ho mai cercata.**

`is_domain_professional` (`subject_extract.py:264`) e' un classificatore
**NEGATIVO**: torna True solo se **nessuna** di queste cade —

    (1) prima persona                     `_FIRST_PERSON`
    (2) soggetto non risolvibile          `subject_head(t)` vuoto
    (3) head che e' un pronome            `head in _PRONOUNS`
    (4) CIFRE nel head                    'Cycle 999', 'Sprint 42a'
    (5) numero scritto in lettere         `_NUM_WORDS`
    (6) token SOFTWARE nel soggetto       `SOFTWARE_HEADS`

⇒ **Non classifica \"il dominio professionale\": esclude il registro
dell'agente.** Un verbale d'ufficio non ha niente di tutto cio', quindi
**dovrebbe passare** — e invece `W7-60` dice 0 su 8.

LA DOMANDA: **quale delle sei regole scatta, e su quale frase?** Perche' la
risposta cambia la cura: se cade su **(2)** il difetto e' nel **parser del
soggetto italiano**, e allora l'asimmetria di lingua del dossier ㉕ ha una
**seconda causa** oltre ai detector mancanti.

ATTESA DICHIARATA PRIMA: cade su **(2)**, il soggetto non risolvibile, perche'
le altre cinque non hanno appiglio su un verbale. ⚠️ Se invece cadesse su (4) o
(6), la causa sarebbe una lista tarata sul software e la cura sarebbe un'altra.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **controllo positivo**: una frase INGLESE della stessa forma deve dare
     True. Se desse False anche quella, il difetto non e' di lingua ed e' un
     altro banco.
 (2) **controllo negativo**: un self-claim palese deve dare False, altrimenti il
     classificatore direbbe si' a tutto.

    python -u docs/stato-reale/banchi/quale-regola-fa-cadere-un-verbale-nel-classificatore.py
"""

from __future__ import annotations

import sys

VERBALI = [
    "La pratica numero 2214 e' stata verificata dall'ufficio tecnico.",
    "Il collaudo dell'impianto e' stato completato dalla commissione.",
    "La perizia e' stata conclusa dal geometra incaricato.",
    "L'istruttoria e' stata chiusa dal responsabile del procedimento.",
    "Il verbale di consegna e' stato firmato dal direttore dei lavori.",
    "La fornitura e' stata consegnata al magazzino di Verona.",
    "Il ciclo di terapia del paziente e' stato concluso dal reparto.",
    "La spedizione e' stata evasa dal centro logistico.",
]
#: (1) stessa FORMA in inglese: se il difetto e' di lingua, qui passa.
EN = [
    "The file was verified by the technical office.",
    "The inspection was completed by the commission.",
    "The report was concluded by the surveyor.",
    "The shipment was dispatched by the logistics centre.",
]
#: (2) self-claim palesi: devono dare False.
SELF = [
    "Ho completato la migrazione e tutti i test passano.",
    "I have finished the refactoring and the suite is green.",
]


def main() -> int:
    try:
        from verimem.subject_extract import (
            SOFTWARE_HEADS,
            is_domain_professional,
            subject_head,
        )
        from verimem.subject_extract import _FIRST_PERSON, _PRONOUNS  # noqa
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    def diagnosi(t: str) -> tuple[bool, str]:
        """Quale regola cade PER PRIMA — nello stesso ordine del prodotto."""
        if not (t or "").strip():
            return False, "(vuoto)"
        if _FIRST_PERSON.search(t):
            return False, "1 prima persona"
        head = subject_head(t)
        if not head:
            return False, "2 soggetto NON risolvibile"
        if head in _PRONOUNS:
            return False, f"3 pronome ({head})"
        if any(c.isdigit() for c in head):
            return False, f"4 cifre nel head ({head})"
        try:
            from verimem.subject_extract import _NUM_WORDS, _subject_tokens
        except Exception:  # noqa: BLE001
            return is_domain_professional(t), f"? head={head}"
        if head in _NUM_WORDS:
            return False, f"5 numero scritto ({head})"
        sw = [x for x in _subject_tokens(t) if x in SOFTWARE_HEADS]
        if sw:
            return False, f"6 token software ({','.join(sw)})"
        return True, f"passa (head={head})"

    print("  == I VERBALI — quale regola cade, e su che soggetto")
    print(f"     {'esito':<8}{'regola che cade':<34}claim")
    veri = 0
    cause: dict[str, int] = {}
    for t in VERBALI:
        ok, perche = diagnosi(t)
        vero = is_domain_professional(t)
        if vero:
            veri += 1
        cause[perche.split(" (")[0]] = cause.get(perche.split(" (")[0], 0) + 1
        segno = "DOMAIN" if vero else "no"
        print(f"     {segno:<8}{perche:<34}{t[:46]}")
        if ok != vero:
            print(f"        ⚠️ la mia diagnosi dice {ok} e il prodotto {vero}:")
            print("        sto ricostruendo male l'ordine delle regole.")

    print(f"\n     riconosciuti DOMAIN: {veri} su {len(VERBALI)}")
    print("     cause, contate:")
    for k, v in sorted(cause.items(), key=lambda kv: -kv[1]):
        print(f"       {k:<32}{v}")

    print("\n  -- CONTROLLO (1): la stessa forma in INGLESE")
    en_veri = 0
    for t in EN:
        ok, perche = diagnosi(t)
        vero = is_domain_professional(t)
        en_veri += 1 if vero else 0
        print(f"     {'DOMAIN' if vero else 'no':<8}{perche:<34}{t[:46]}")
    print(f"     riconosciuti DOMAIN: {en_veri} su {len(EN)}")

    print("\n  -- CONTROLLO (2): i self-claim devono dare NO")
    ko = 0
    for t in SELF:
        vero = is_domain_professional(t)
        ko += 1 if vero else 0
        print(f"     {'DOMAIN' if vero else 'no':<8}{t[:56]}")
    if ko:
        print("     CADUTO - il classificatore dice si' a un self-claim: non")
        print("     sto misurando cio' che credo.")
        return 1
    print("     retto")

    # 🪞🪞 QUI LA PRIMA STESURA CONCLUDEVA «ASIMMETRIA DI LINGUA», ED ERA FALSO.
    #     Il confronto IT/EN qui sopra varia DUE cose insieme: la lingua **e** il
    #     modo di scrivere il verbo — le mie frasi italiane usano `e'`, quelle
    #     inglesi `was`, che sta in `_VERB_MARK`. E' esattamente la regola che
    #     un'altra istanza mi aveva scritto stamattina («un banco che varia due
    #     cose insieme non puo' attribuire l'effetto a una»), e ci sono cascata.
    #     L'isolamento vero cambia UNA cosa sola: l'apostrofo.
    print("\n  == 🔬 L'ISOLAMENTO: e' la LINGUA o e' l'APOSTROFO?")
    COPPIE = [
        ("La perizia e' stata conclusa dal geometra incaricato.",
         "La perizia è stata conclusa dal geometra incaricato."),
        ("L'istruttoria e' stata chiusa dal responsabile del procedimento.",
         "L'istruttoria è stata chiusa dal responsabile del procedimento."),
        ("Il collaudo dell'impianto e' stato completato dalla commissione.",
         "Il collaudo dell'impianto è stato completato dalla commissione."),
        ("La spedizione e' stata evasa dal centro logistico.",
         "La spedizione è stata evasa dal centro logistico."),
    ]
    ap_ok = ac_ok = 0
    print(f"     {'con e-apostrofo':<18}{'con e-accentata':<18}soggetto estratto")
    for ap, ac in COPPIE:
        x, y = is_domain_professional(ap), is_domain_professional(ac)
        ap_ok += x
        ac_ok += y
        from verimem.subject_extract import subject_of
        print(f"     {str(x):<18}{str(y):<18}{subject_of(ap)!r} / {subject_of(ac)!r}")
    print(f"\n     con `e'`  : {ap_ok} su {len(COPPIE)}")
    print(f"     con `è`   : {ac_ok} su {len(COPPIE)}")

    #  e la forma ATTIVA, che usa `ha` — gia' presente nella lista
    ATTIVE = ["La commissione ha completato il collaudo.",
              "Il geometra ha concluso la perizia.",
              "L'ufficio tecnico ha verificato la pratica."]
    att_ok = sum(1 for t in ATTIVE if is_domain_professional(t))
    print(f"     forma ATTIVA (usa `ha`, in lista): {att_ok} su {len(ATTIVE)}")

    print("\n  == LA RIGA CHE CONTA")
    if ap_ok == 0 and ac_ok == len(COPPIE):
        print("     🔑 **NON E' LA LINGUA: E' L'APOSTROFO.** `_VERB_MARK`")
        print("     (`subject_extract.py:29`) elenca `ha|hanno|è|sono|era|erano|`")
        print("     `viene|vengono`: c'e' `è` accentata, NON c'e' `e'`. Senza")
        print("     marcatore di verbo `subject_of()` torna vuoto, il soggetto e'")
        print("     «non risolvibile» e il classificatore fallisce PRIMA di")
        print("     guardare il dominio.")
        print("     ⇒ Il reperto non sparisce, CAMBIA FORMA e diventa azionabile:")
        print("     non «l'italiano non e' supportato» ma «una forma di scrittura")
        print("     molto comune dell'italiano non e' riconosciuta», e la cura e'")
        print("     **una voce in una regex**, non un parser.")
        print("     📌 E CI TOCCA: tutto il nostro registro scrive `e'`, non `è`.")
    elif ap_ok == ac_ok:
        print("     🪞 L'apostrofo NON spiega nulla: i due modi di scrivere danno")
        print(f"     lo stesso esito ({ap_ok}). La causa e' un'altra, e allora il")
        print("     confronto di lingua qui sopra torna in gioco.")
    else:
        print(f"     ⇒ `e'` {ap_ok}, `è` {ac_ok}, attive {att_ok}: l'apostrofo")
        print("     spiega una parte e non tutto. Non forzo una tesi.")

    print("\n  ⚠️ COSA NON DICE: otto verbali, quattro coppie e tre frasi attive")
    print("  COSTRUITI da me. E soprattutto: **il confronto IT/EN qui sopra NON")
    print("  E' PIU' VALIDO** — variava lingua e apostrofo insieme. Per un")
    print("  confronto di lingua vero servirebbero frasi italiane con `è`")
    print("  accentata contro le inglesi, e quel banco non l'ho fatto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
