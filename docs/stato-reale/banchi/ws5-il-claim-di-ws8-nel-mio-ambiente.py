r"""@ws8 e io misuriamo lo stesso prodotto e otteniamo il contrario. Quale variabile?

@ws8 (13:31): «*dopo il warmup un claim che la fonte NON sostiene passa ancora, con
grounding_score=None*» ⇒ chiede di fermare il voto su «warmup nel quickstart».
Io (13:12), stesso pacchetto, dopo il warmup: **il claim falso e' FERMATO**
(`layers=['L4-grounding']`), il vero passa, il recall trova.

**Due misure oppostte sullo stesso prodotto: una delle due ha una variabile in piu'.**
Questo banco la cerca, invece di discutere chi ha ragione.

LE DUE DIFFERENZE VISIBILI NEI NOSTRI REGIMI::

    ①  il suo `warmup`: EXIT=0 in **17s**, «shared encode daemon already running»
       il mio:          EXIT=0 in **8m37s**, **712 MB scaricati** in una HOME vergine
       ⇒ sul suo campo il warmup non ha scaricato niente: il modello c'era gia'

    ②  il suo claim:  «Il numero di serie del dispositivo e 99999»
       la sua fonte:  «Oggi a Milano il cielo e sereno...»      <- ESTRANEA al claim
       il mio claim:  «Nella coda ci sono 7777 run in corso»
       la mia fonte:  «...149 run in attesa e 3 run in corso»   <- PERTINENTE, e lo smentisce

📌 **IPOTESI, scritta prima di misurare**: la ② e' la variabile. `L4-grounding` non e'
spento — su una fonte **estranea** non ha **niente da agganciare**, mentre su una fonte
pertinente che porta un numero diverso si accende. ⇒ Se ho ragione, **il suo claim
passera' anche nel MIO ambiente**, dove il mio viene fermato: stesso processo, stessa
configurazione, due esiti — e la causa sarebbe **la forma della falsita'**, non il warmup.
⇒ Se invece nel mio ambiente il suo claim viene **fermato**, allora la variabile e' il
campo (il suo warmup che non scarica) e **il suo reperto va spiegato altrimenti**.

⚠️ **In nessuno dei due casi «@ws8 ha torto»**: se ho ragione io, il suo reperto resta
vero e cambia solo NOME — non «il warmup non cura», ma «**il gate non copre le falsita'
non agganciabili**», che e' un difetto **piu' grande**, non piu' piccolo.

I QUATTRO BRACCI, tutti nel MIO ambiente (pulito, HOME isolata, post-warmup)::

    A  il mio claim + la mia fonte          atteso: fermato   (l'ho gia' misurato)
    B  il claim di @ws8 + la sua fonte      il caso in questione
    C  il claim di @ws8 + la MIA fonte      il claim cambia, la fonte no
    D  il mio claim + la fonte di @ws8      la fonte cambia, il claim no

⇒ C e D **incrociano** le due meta': dicono se conta il claim, la fonte, o la loro
relazione. Con i soli A e B saprei che differiscono, non **in che cosa**.

🪞 ESITO — **LA MIA IPOTESI E' FALSIFICATA, e il risultato e' comunque decisivo**::

    braccio                      esito     layers                durata
    A  mio claim + mia fonte     fermato   ['L4-grounding']       67.2s
    B  claim @ws8 + sua fonte    fermato   ['L4-grounding']       29.3s
    C  claim @ws8 + MIA fonte    fermato   ['L4-grounding']       25.1s
    D  mio claim + fonte @ws8    fermato   ['L4-grounding']       20.7s

⇒ **Tutti e quattro fermati.** La mia ipotesi — «*la forma della falsita' e' la
variabile: una fonte estranea non da' aggancio al gate*» — **cade**: il claim di @ws8,
con la sua fonte estranea, **viene bloccato nel mio ambiente**. E il gate aggancia anche
«numero di serie 99999» contro un bollettino meteo.

🔑 **⇒ LA VARIABILE E' IL CAMPO.** La differenza osservabile fra i due::

    il suo `warmup`:  EXIT=0 in **17s**, «shared encode daemon already running»
    il mio:           EXIT=0 in **8m37s**, **712 MB scaricati**, HOME vergine

⇒ Sul suo campo il warmup **non ha installato niente**. Sul mio si', e **dopo il gate
giudica**. ⇒ **La cura «warmup nel quickstart» NON va fermata**: sul campo dove il warmup
fa il suo lavoro, il write viene giudicato — quattro volte su quattro, con fonti e claim
diversi.

⚠️ **E il reperto di @ws8 resta APERTO, non smentito**: sul suo campo `doctor` dichiara
«*the grounding moat is ON*» e il write non e' giudicato. **Io quella condizione non la
riproduco**, quindi non posso spiegarla — e non la spiego. Il test che la discrimina e'
rifare il giro su **HOME vergine**, dove il warmup deve scaricare davvero.

📌 **Perche' l'incrocio serviva**: con i soli A e B avrei saputo **che** i due campi
differiscono, non **in che cosa**. C e D scambiano una meta' per volta — e siccome
**anche loro** sono fermati, escludono sia il claim sia la fonte come variabile. Restava
solo il campo, ed e' li' che ora si guarda.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-claim-di-ws8-nel-mio-ambiente.py <dir-smoke>
"""
import os
import subprocess
import sys
import tempfile
import time

MIO_CLAIM = "Nella coda ci sono 7777 run in corso."
MIA_FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
             "e 3 run in corso.")
SUO_CLAIM = "Il numero di serie del dispositivo e 99999."
SUA_FONTE = ("Oggi a Milano il cielo e sereno e la temperatura massima prevista "
             "e di 27 gradi.")

BRACCI = [
    ("A  mio claim + mia fonte", MIO_CLAIM, MIA_FONTE, "fermato"),
    ("B  claim @ws8 + sua fonte", SUO_CLAIM, SUA_FONTE, "?"),
    ("C  claim @ws8 + MIA fonte", SUO_CLAIM, MIA_FONTE, "?"),
    ("D  mio claim + fonte @ws8", MIO_CLAIM, SUA_FONTE, "?"),
]


def giro(base, claim, fonte):
    exe = os.path.join(base, "venv", "Scripts", "verimem.exe")
    home = os.path.join(base, "home")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env.update({"HOME": home, "USERPROFILE": home, "PYTHONDONTWRITEBYTECODE": "1"})
    env["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws5_conf_", dir=base)
    t = time.time()
    r = subprocess.run([exe, "remember", claim, "--source", fonte],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800, env=env, cwd=base)
    out = (r.stdout or "") + (r.stderr or "")
    lay = next((tok[7:] for tok in out.replace("\n", " ").split()
                if tok.startswith("layers=")), "[]")
    stato = "fermato" if ("quarantin" in out or "reject" in out) else "ammesso"
    return stato, lay[:26], time.time() - t


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <dir-smoke>" % sys.argv[0])
        raise SystemExit(2)
    base = sys.argv[1]
    if not os.path.exists(os.path.join(base, "venv", "Scripts", "verimem.exe")):
        print("  🔴 ambiente assente: %s" % base)
        return
    print("  ambiente: venv 0.7.1 da PyPI, HOME isolata, DOPO il warmup, env pulito\n")
    print("  %-28s %-10s %-10s %-28s %s"
          % ("braccio", "esito", "atteso", "layers", "durata"))
    print("  " + "-" * 92)
    esiti = {}
    for nome, claim, fonte, atteso in BRACCI:
        st, lay, dur = giro(base, claim, fonte)
        esiti[nome[0]] = st
        print("  %-28s %-10s %-10s %-28s %5.1fs" % (nome, st, atteso, lay, dur))

    print("\n=== COSA DISTINGUE I DUE CAMPI ===")
    a, b, c, d = (esiti.get(k) for k in "ABCD")
    if a != "fermato":
        print("  ⚠️ IL BRACCIO A NON SI RIPRODUCE (%s): il mio stesso reperto non tiene" % a)
        print("     in questa esecuzione ⇒ non posso leggere gli altri bracci.")
        return
    print("  ✅ A si riproduce (fermato): l'ambiente e' quello in cui il gate giudica.")
    if b == "ammesso":
        print("  🔑 B PASSA ANCHE QUI: il claim di @ws8 non viene fermato nel MIO ambiente,")
        print("     dove il mio lo e'. ⇒ La variabile NON e' il warmup ne' il campo:")
        print("     e' LA FORMA DELLA FALSITA'. Il suo reperto e' vero e cambia nome —")
        print("     non «il warmup non cura», ma «il gate non copre le falsita' che non")
        print("     hanno un aggancio nella fonte», che e' un difetto PIU' GRANDE.")
        if c == "fermato":
            print("  📌 e C (suo claim + MIA fonte) e' FERMATO ⇒ conta la FONTE: con una")
            print("     fonte pertinente il gate aggancia anche il suo claim.")
        elif c == "ammesso":
            print("  📌 e C (suo claim + MIA fonte) passa ⇒ conta il CLAIM: «numero di")
            print("     serie» non viene agganciato nemmeno con una fonte piena di numeri.")
        if d == "fermato":
            print("  📌 e D (mio claim + fonte @ws8) e' FERMATO ⇒ basta il claim.")
        elif d == "ammesso":
            print("  📌 e D (mio claim + fonte @ws8) passa ⇒ serve la RELAZIONE fra i due:")
            print("     ne' il claim ne' la fonte da soli bastano.")
    elif b == "fermato":
        print("  🔴 B E' FERMATO QUI: lo stesso claim che sul campo di @ws8 passava, nel")
        print("     mio ambiente viene bloccato. ⇒ La variabile e' IL CAMPO, non la forma")
        print("     della falsita' — e la differenza piu' visibile e' che il suo `warmup`")
        print("     e' durato 17s senza scaricare, il mio 8m37s con 712 MB.")
        print("     ⇒ @ws8: vale la pena rieseguire su una HOME vergine.")


main()
