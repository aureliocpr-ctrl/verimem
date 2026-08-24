"""«_entita_diverse è True» NON vuol dire «il ramo proper l'ha deciso».

Banco per il disaccordo aperto il 24/08 fra @ws4 (togliere `if ea or eb:
return True`) e @ws6 (tenerlo, aggiornando i presidi). Non decide al posto di
nessuna: dà il RIGHELLO che finora mancava a tutte e tre.

═══ IL PROBLEMA DI MISURA ═══
Il ramo vive DENTRO `_entita_diverse` come closure (`_proper`, riga 1157): non
è chiamabile né monkeypatchabile dall'esterno. Le due vie sbagliate:

  ⛔ RICOSTRUIRE la logica nel banco. È la trappola che mi è costata il 21/08:
     un righello che reimplementava `_entita_diverse` divergeva dalla funzione
     vera su **1515 coppie su 1933**, e avevo consegnato «39 salvate / 0 perse»
     quando i veri erano **27 e 1**.
  ⛔ Contare `_entita_diverse(a, b) == True`. Misura l'ESITO, non l'AUTORE:
     SIB_BARE è True anche SENZA il ramo (vedi sotto).

  ✅ LA VIA: A/B sul SORGENTE VERO nella stessa esecuzione. Si prende la
     funzione con `inspect.getsource`, se ne compila una variante con quelle
     due righe — e solo quelle — rimosse, e si confrontano. Non è una
     reimplementazione: è il codice di produzione meno un ramo.
     Un A/B nella stessa esecuzione è anche immune al problema dei due SHA.

═══ IL CONTROLLO POSITIVO, che viene PRIMA del numero ═══
Il banco si RIFIUTA di misurare se il ramo non è isolabile (`count != 1`) e se
non riconosce il caso noto. @ws7 ha dovuto ritirare un numero proprio perché il
suo righello non discriminava: è la prova che il presidio serve.

═══ ESITO, 24/08 19:45, su 82d240e6 ═══

    SIB_FP      originale=True  senza_ramo=True    <- NON è il ramo proper
    SIB_SAME    originale=True  senza_ramo=False   <- il ramo decide DA SOLO
    SIB_RENAME  originale=True  senza_ramo=False   <- il ramo decide DA SOLO
    SIB_BARE    originale=True  senza_ramo=True    <- NON è il ramo proper

⇒ **2 su 4.** Il fatto in memoria `cdb22d587104` riporta `[('SIB_SAME', True),
('SIB_RENAME', True), ('SIB_BARE', True)]`: i valori sono giusti, ma `True` da
solo non attribuisce la decisione al ramo.

═══ IL CASO CHE MI ACCUSA, e lo dico da autrice del ramo ═══
    CANDIDATE  "**The payments team** migrated to Stripe in 2025."
    SIB_SAME   "**The payments team** still runs on the legacy processor."

Stesso soggetto, contraddizione vera — ed è quella che il layer semantico
esiste per prendere. Il ramo la sopprime perché «Stripe» sta da un lato solo.
`if ea or eb` non guarda DOVE sta il nome proprio: qui è nel complemento, non
nel soggetto, e non rende diverse le entità — rende una frase più specifica.

⛔ COSA QUESTO BANCO NON DICE: la taglia sul corpus. Ci ho provato contando le
coppie adiacenti nello stesso topic e ho ottenuto 133 su 2311 (5,76%), un
numero dall'aria di risposta che NON ho consegnato: guardando quattro righe di
ciò che avevo contato, erano fatti scorrelati («l'animale preferito di Aurelio»
contro «quanti file ci sono nel filesystem»). Il prodotto chiama
`_entita_diverse` su *contradicting OLD fact ids* (anti_confab_gate.py:650),
cioè su coppie che un rilevatore ha GIÀ segnalato. La popolazione giusta è
quella; questo banco non la costruisce.
"""
from __future__ import annotations

import inspect

import verimem.anti_confab_gate as G

RAMO = "    if ea or eb:\n        return True\n"

CANDIDATE = "The payments team migrated to Stripe in 2025."
SIBLING = {
    "SIB_FP": "The design team runs a weekly critique on Fridays.",
    "SIB_SAME": "The payments team still runs on the legacy processor.",
    "SIB_RENAME": "The checkout squad reverted to the legacy processor.",
    "SIB_BARE": "The team adopted a new processor.",
}


def senza_il_ramo():
    """La funzione di produzione meno il ramo proper. Solleva se il ramo non
    è isolabile: un banco che non sa cosa sta togliendo non misura niente."""
    src = inspect.getsource(G._entita_diverse)
    n = src.count(RAMO)
    if n != 1:
        raise SystemExit(
            f"IL BANCO SI RIFIUTA DI MISURARE: il ramo compare {n} volte nel "
            f"sorgente, non 1. Se è stato riscritto, questo righello va "
            f"rifatto — non adattato.")
    ns = dict(G.__dict__)
    exec(compile(src.replace(RAMO, ""), "<senza-ramo>", "exec"), ns)
    return ns["_entita_diverse"]


def controllo_positivo(senza) -> bool:
    """Il righello deve riconoscere il caso noto PRIMA di misurare altro."""
    casi = [
        ("caso noto Stripe / —", CANDIDATE, SIBLING["SIB_RENAME"], True, False),
        ("teste uguali, proper asimm.", CANDIDATE, SIBLING["SIB_SAME"], True, False),
        ("nessun proper", SIBLING["SIB_SAME"], SIBLING["SIB_RENAME"], False, False),
    ]
    ok = True
    print("=== CONTROLLO POSITIVO DEL RIGHELLO ===")
    for nome, a, b, att_o, att_s in casi:
        o, s = G._entita_diverse(a, b), senza(a, b)
        buono = (o == att_o and s == att_s)
        ok = ok and buono
        print("   %-28s originale=%-5s senza_ramo=%-5s  %s"
              % (nome, o, s, "OK" if buono else "<<< NON DISCRIMINA"))
    return ok


def main() -> None:
    senza = senza_il_ramo()
    if not controllo_positivo(senza):
        raise SystemExit(
            "\n⛔ IL RIGHELLO NON DISCRIMINA: non consegnare nessun numero "
            "preso con esso. È quello che è successo a @ws7 il 24/08.")
    print("\n=== A/B: CANDIDATE contro ogni sibling ===")
    print("   (True = entità diverse = il ritiro NON passa = il layer tace)")
    decisi = 0
    for nome, testo in SIBLING.items():
        o, s = G._entita_diverse(CANDIDATE, testo), senza(CANDIDATE, testo)
        solo = o and not s
        decisi += bool(solo)
        print("   %-11s originale=%-5s senza_ramo=%-5s%s"
              % (nome, o, s, "   <<< IL RAMO PROPER decide DA SOLO" if solo else ""))
    print("\nsibling su cui il ramo proper decide DA SOLO: %d su %d"
          % (decisi, len(SIBLING)))


if __name__ == "__main__":
    main()
