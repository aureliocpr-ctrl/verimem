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

    print("\n  == LA RIGA CHE CONTA")
    prima = max(cause.items(), key=lambda kv: kv[1])[0] if cause else "-"
    if veri == 0 and en_veri > 0:
        print(f"     🔴 ASIMMETRIA DI LINGUA NEL CLASSIFICATORE: {veri} su"
              f" {len(VERBALI)} in italiano contro {en_veri} su {len(EN)} in")
        print(f"     inglese, e la regola che cade e' «{prima}».")
        print("     ⇒ La carve-out `domain-precision` non e' rotta: **non arriva**")
        print("     ai verbali italiani, e il dossier ㉕ ha una SECONDA causa")
        print("     oltre ai detector mancanti.")
    elif veri == 0:
        print(f"     ⇒ Zero in entrambe le lingue, regola «{prima}»: NON e' un")
        print("     difetto di lingua. La causa e' un'altra e non la forzo.")
    else:
        print(f"     ⇒ {veri} su {len(VERBALI)} in italiano, {en_veri} su"
              f" {len(EN)} in inglese. Il quadro non e' netto.")

    print("\n  ⚠️ COSA NON DICE: otto verbali e quattro frasi inglesi COSTRUITI")
    print("  da me, con la forma dei casi d'ufficio, non quei casi. E la")
    print("  diagnosi ricostruisce l'ordine delle regole leggendo il codice:")
    print("  dove il mio esito e quello del prodotto divergono, lo stampo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
