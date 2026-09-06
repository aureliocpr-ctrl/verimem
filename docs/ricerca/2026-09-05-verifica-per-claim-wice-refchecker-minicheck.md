# Verificare per claim: WiCE, RefChecker, MiniCheck — e che cosa cambiano per noi

**ws3 «Galileo» · 05/09/2026 20:50 · letto PRIMA del banco** (regola 5 dell'agenzia).
Continua `2026-09-04-decomposizione-in-claim-atomici-letteratura.md` (FActScore,
Molecular Facts, VeriScore, Decomposition Dilemmas, DnDScore). Serve al **muro 1,
fase 2**: la tesi del lead — *write = N claim atomici, ognuno giudicato* — dopo che
ieri ho misurato il suo danno collaterale (2/10 veri sulle 15, 16/800 sul campione) e
il suo costo (0,79× in lotto).

La domanda con cui sono andato a leggere: **qual è l'unità giusta da giudicare, e come
si evita di giudicare un pezzo che non è un claim?**

---

## Le tre fonti, con l'URL e ciò che ognuna decide

| lavoro | URL | che cosa aggiunge alla nostra decisione |
|---|---|---|
| **WiCE** — Kamoi, Goyal, Rodriguez, Durrett, EMNLP 2023 | https://arxiv.org/abs/2303.01432 · https://github.com/ryokamoi/wice | entailment su **sub-frasi del claim**, ciascuna con l'insieme minimo di frasi di evidenza. La decomposizione automatica (GPT-3.5) **migliora i modelli di entailment al test**, non solo la valutazione: è la prova che decomporre PRIMA di giudicare paga anche per il giudice, non solo per chi misura. |
| **RefChecker** — Amazon Science, 2024 | https://arxiv.org/abs/2405.14486 · https://github.com/amazon-science/RefChecker | l'unità è la **tripletta (soggetto, predicato, oggetto)**; su 11k triplette annotate da 2,1k risposte di 7 LLM, la tripletta batte risposta, frase e sub-frase di **6,8–26,1 punti**. Tre regimi: contesto zero, rumoroso, accurato. |
| **MiniCheck** — Tang, Laban, Durrett, EMNLP 2024 | https://arxiv.org/abs/2404.10774 · https://github.com/Liyan06/MiniCheck | un modello da **770M** (Flan-T5) arriva a GPT-4 sul fact-checking su documento, addestrato su **errori fattuali sintetici a livello di frase**; benchmark LLM-AggreFact (11 dataset). Costo per chiamata di ordini di grandezza sotto un LLM. |

---

## La concatenazione (B4): dai nostri dati alla tesi di oggi

1. **Ieri, misurato**: la decomposizione del lead ferma 2/10 veri sulle 15 e 16/800 sul
   campione non scelto. Guardando *quali*: frammenti degeneri («Indietro 16 con
   tracciato 0.»), citazioni spezzate, completamenti nudi («Finito alle 22:32.»).
2. **RefChecker**: l'unità giusta è una tripletta S-P-O. Un frammento senza soggetto o
   senza predicato **non è una tripletta** — non è un claim, è un pezzo di claim.
3. **WiCE**: decomporre prima di giudicare aiuta il giudice, quindi la direzione del
   lead è quella giusta; il problema non è decomporre, è *che cosa* si manda al giudice.
4. **Molecular Facts** (ieri): «fully atomic facts are not the right representation» —
   la minimalità va bilanciata con la decontestualità.

⇒ **Tesi**: i veri che cadono cadono perché il pezzo *non ha la forma di un claim*, e
un **filtro di forma** — «giudica solo i pezzi con soggetto e verbo finito» — toglie il
danno senza togliere il guadagno. Il filtro non lo invento: è
`verimem.subject_extract.subject_of`, che torna vuoto quando non c'è un soggetto
davanti a un verbo finito. Predizioni T1–T4 depositate sul canale (`fc8b697a4d90ce14`,
20:55) prima di eseguire.

**E MiniCheck dice una cosa sul nostro giudice**: ieri (P3) il nostro CE non si
distingue da un conta-parole sulle contraddizioni implicite. MiniCheck ottiene
prestazioni da GPT-4 con 770M parametri **perché è addestrato su errori sintetici
costruiti a livello di frase** — non perché è grande. È un'indicazione per ws4 (giudice
v3.2): la via non è muovere i pesi, è il *dato* d'addestramento. Lo passo, non lo
eseguo: non è il mio perimetro.

**Precisazione dovuta, perché il nome è già nei miei banchi**: lo scorer **C** di ieri
(`ws3-P3-la-popolazione-implicita-contro-quattro-scorer`, commit `f3907dd9`) *è*
`lytang/MiniCheck-DeBERTa-v3-Large`, cioè la variante DeBERTa di MiniCheck. Sulle 30
contraddizioni implicite **non è risultato distinguibile** dal nostro giudice né dal
conta-parole (intervallo appaiato che include lo zero); l'unico decidibilmente migliore
era **B** (`MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli`, +0,2856). Quindi
«MiniCheck arriva a GPT-4» vale sul *loro* benchmark (LLM-AggreFact, inglese, grounding
su documento), non sulle nostre implicite in italiano: le varianti **FT5 (770M)** e
**Bespoke-7B** non le ho misurate, e non le do per migliori.

---

## Che cosa questa lettura NON decide

- Nessuna delle tre misura su **italiano**; RefChecker estrae le triplette con un LLM,
  noi con una regex. Se il filtro di forma fallisce, fallisce `subject_of` in
  italiano, non l'idea della tripletta.
- MiniCheck verifica *contro un documento*; il nostro L1 a `ground=False` non ha
  documento. La tesi del filtro vale per il gate lessicale; per il moat va rimisurata.
- Ho letto abstract, README e pagine HTML, non i PDF interi.

*Nota di metodo*: questa pagina sta in `docs/ricerca/`, versionata e citabile, e non
nello store di Aurelio, che tengo in sola lettura finché non è Aurelio a dirmi altro.
