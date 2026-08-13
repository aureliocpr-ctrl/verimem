"""Il flip giapponese è visto — e NON dipende più dai quindici millesimi.

⚠️⚠️ AGGIORNATO POCHE ORE DOPO ESSERE STATO SCRITTO, e il motivo è il punto.
Questo file nacque per presidiare un margine: `negation_conflict` confrontava
le due frasi coi **bigrammi** di `content_tokens`, e il giapponese superava la
soglia di 0.6 con 0.615 — quindici millesimi. La cura al CJK ha poi spostato
quel confronto sui **caratteri** (`_token_di_confronto`), e il margine non è più
ciò che tiene in piedi il flip.

⇒ La misura qui sotto resta vera e resta utile — 8 token condivisi su 13 è una
proprietà di `content_tokens`, che è ancora usata da `corroboration` e
`facts_conflict` — ma **non è più la ragione per cui il giapponese funziona**.
Lasciare il docstring di prima avrebbe prodotto esattamente il difetto che
questo repository insegue: un documento verde che descrive un mondo passato.

═══ IL TESTO ORIGINALE, tenuto perché la storia serve ═══

Il flip giapponese era visto con un margine di 0,015 sulla soglia.

`negation_conflict` pretende che le due frasi siano quasi identiche una volta
tolto il negatore — Jaccard ≥ 0.6 sui token di contenuto. In inglese quella
guardia è larghissima: togliere «not» lascia le altre parole intatte, e il
Jaccard resta 1.000. Nelle scritture senza spazi no.

Misurato oggi::

    システムは署名されました / システムは署名されません
      token condivisi 8 · unione 13 · JACCARD 0.615   soglia 0.600

**Margine 0,015.** Il flip giapponese non passa perché il meccanismo lo regge
comodamente: passa per quindici millesimi.

═══ 🔑 PERCHÉ QUESTO FILE ESISTE, VISTO CHE OGGI È VERDE ═══

La segmentazione CJK produce **bigrammi**, e un negatore che sta *dentro* la
frase — non separato da spazi — se lo si toglie riscrive i bigrammi che lo
attraversano: alcuni muoiono, altri nascono, e il token «stringa intera» non
coincide mai fra i due lati. Il denominatore del Jaccard cresce mentre il
numeratore no.

Il cinese, che ha lo stesso meccanismo e negatori più corti, **cade**: misurato
1 flip visto su 5, con Jaccard 0.286 / 0.286 / 0.400 / 0.500. Il giapponese sta
sopra la soglia perché le sue frasi sono più lunghe e i suffissi verbali
condividono più bigrammi — non per una proprietà del rilevatore.

⇒ Chiunque tocchi la soglia, `content_tokens`, o la segmentazione CJK può
spegnere il flip giapponese **senza aver toccato niente che si chiami
"giapponese"**. Questo file è il rosso che glielo dice, e il messaggio d'errore
riporta il numero perché la diagnosi non richieda di rifare la misura.

📌 Il cinese NON è un blocco e qui non viene preteso: il README dichiara il
proprio perimetro — «measured EN/IT/FR/ES», sotto un titolo che dice «Honest
scope of the CE-only judge». Aggiungere un'asserzione sul cinese renderebbe
rosso un file per una promessa che il prodotto non fa.
"""
from __future__ import annotations

from verimem.quantity_match import _senza_negatori, content_tokens, negation_conflict

#: Affermazione e sua negazione, identiche in tutto il resto.
AFFERMA = "システムは署名されました"
NEGA = "システムは署名されません"

#: La guardia dentro `negation_conflict`. Scritta qui perché il test possa
#: RIPORTARE il margine: se un domani la soglia nel codice cambiasse, il primo
#: test qui sotto resta il giudice vero (misura il comportamento, non il numero).
SOGLIA_DICHIARATA = 0.6


def _jaccard(a: str, b: str) -> tuple[int, int, float]:
    ca = content_tokens(_senza_negatori(a))
    cb = content_tokens(_senza_negatori(b))
    condivisi, unione = ca & cb, ca | cb
    return len(condivisi), len(unione), (len(condivisi) / len(unione) if unione else 0.0)


def test_il_flip_giapponese_e_ancora_visto():
    """Il cuore: la frase e la sua negazione devono contraddirsi.

    Se cade, il messaggio dice ANCHE di quanto si è scesi — la causa quasi
    certa è la guardia di somiglianza, non il negatore.
    """
    condivisi, unione, j = _jaccard(AFFERMA, NEGA)
    assert negation_conflict(AFFERMA, NEGA) is not None, (
        f"il flip giapponese non è più visto. Jaccard misurato ora: "
        f"{condivisi}/{unione} = {j:.3f} contro una soglia di "
        f"{SOGLIA_DICHIARATA}. Passava per 0,015: se hai toccato la "
        f"segmentazione CJK, `content_tokens` o la soglia, è quello")


def test_IL_MARGINE_E_SOTTILE_e_questo_test_lo_dichiara():
    """⚠️ Non un secondo giudice: un cartello.

    Il test sopra diventa rosso quando il danno è fatto. Questo dice, a chi
    legge il file prima di modificarlo, **quanto poco** ci vuole — e diventa
    rosso anche se il margine cambia in MEGLIO, perché in quel caso qualcuno ha
    curato la segmentazione CJK e questa documentazione va riscritta (con il
    cinese, che oggi è a 1 su 5, probabilmente diventato verde).
    """
    condivisi, unione, j = _jaccard(AFFERMA, NEGA)
    assert (condivisi, unione) == (8, 13), (
        f"i token del giapponese non sono più 8 su 13 ma {condivisi} su "
        f"{unione} (Jaccard {j:.3f}): la segmentazione CJK è cambiata. Se in "
        f"meglio, misura di nuovo anche il cinese — era 1 flip su 5 — e "
        f"aggiorna il docstring in cima invece di allargare questo numero")


def test_LA_STESSA_POLARITA_NON_E_UN_CONFLITTO_in_giapponese():
    """⚠️ La popolazione opposta, senza la quale i due sopra non provano nulla.

    Un rilevatore che restituisse un conflitto per qualunque coppia di frasi
    giapponesi simili li renderebbe entrambi verdi mentre ritira fatti veri.
    """
    assert negation_conflict(AFFERMA, AFFERMA) is None
    assert negation_conflict(NEGA, NEGA) is None
