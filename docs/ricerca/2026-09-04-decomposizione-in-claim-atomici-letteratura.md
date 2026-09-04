# Decomporre in claim atomici: che cosa hanno già misurato gli altri

**ws3 «Galileo» · 04/09/2026 20:55 · letto PRIMA del banco** (regola 5 dell'agenzia:
internet prima del banco). Serve al **muro 1** — la tesi del lead (`a05dd7a6d6fa2458`,
04/09 20:16): *decomporre scrittura e fonte in unità atomiche e giudicare a coppie
(MIN sui claim, MAX sulle frasi della fonte)*.

La domanda con cui sono andato a leggere non era «che cos'è FActScore», era quella che
il **residuo dichiarato dal lead** pone: il suo caso P3 («Dopo che il tecnico ha
collaudato l'impianto, la funzionalità è verificata») non si spezza sulle coordinate.
Quindi: **come tratta la letteratura le subordinate, e che prezzo ha già misurato per
la decomposizione?**

---

## Le cinque fonti, con l'URL e ciò che ognuna decide

| lavoro | URL | che cosa aggiunge alla nostra decisione |
|---|---|---|
| **FActScore** — Min et al., EMNLP 2023 | https://arxiv.org/abs/2305.14251 | l'idea originale: spezzare la generazione in **fatti atomici auto-contenuti** e contare quelli sostenuti. È da qui che viene l'eredità del soggetto nello splitter del lead. |
| **Molecular Facts** — Gunjal & Durrett, EMNLP 2024 | https://arxiv.org/abs/2406.20079 | *«fully atomic facts are not the right representation»*. Due desiderata **in tensione**: **decontestualità** (il pezzo sta in piedi da solo) e **minimalità** (quanto poco si aggiunge per ottenerla). |
| **VeriScore** — Song et al., Findings EMNLP 2024 | https://arxiv.org/abs/2406.19276 | sull'estrazione di SAFE l'analisi umana trova **over-decomposition** con sovrapposizione di significato ed estrazione di claim vaghi/non verificabili. La cura non è uno splitter migliore: è estrarre **solo i claim verificabili**, con contesto inter-frase. |
| **Decomposition Dilemmas** | https://arxiv.org/abs/2411.02400 | la decomposizione ha impatto **incoerente** in letteratura: c'è un compromesso fra il guadagno in accuratezza e il **rumore introdotto** dalla decomposizione stessa. |
| **DnDScore** — EMNLP 2025 | https://arxiv.org/abs/2412.13175 · https://aclanthology.org/2025.emnlp-main.1205.pdf | **misura** quella tensione: il **19,11%** dei giudizi cambia fra la forma decomposta e quella decontestualizzata. Enumera i modi di sbagliare: falsi negativi da contesto mancante, e **falsi positivi da contesto AGGIUNTO sbagliato**. |

### Le subordinate: la risposta della letteratura, e il suo limite
Nessuno dei lavori letti tratta la subordinata come categoria a sé. DnDScore, che è il
più vicino, fonda la decomposizione su una teoria (russelliana / neo-davidsoniana) e
punta all'atomicità; il problema delle subordinate **non è enumerato come classe**.
La risposta implicita è un'altra: **non si spezza meglio, si decontestualizza** — cioè
si riscrive il pezzo perché stia in piedi da solo. È esattamente ciò che il lead ha
già fatto a mano al secondo giro (ereditare il soggetto).

Il prezzo di quella risposta, però, è misurato: **19,11%** di giudizi che cambiano, e
il caso in cui il contesto aggiunto è **sbagliato** e maschera la verità del claim.
Cioè: l'eredità del soggetto non è gratis, è uno scambio di un modo di sbagliare con
un altro. La letteratura dice quanto costa lo scambio; non dice che è gratuito.

---

## La concatenazione (B4): dove i nostri dati escono dal perimetro di quei lavori

Tutti e cinque misurano la decomposizione su **verifica contro una fonte**: c'è sempre
un documento, e un pezzo che perde il contesto diventa *non verificabile* o *verificato
male*.

**Noi la applichiamo anche dove la fonte non c'è.** Il muro 1b del lead gira a
`ground=False`: lì il gate non verifica niente, è un **rilevatore lessicale di
self-claim**. In quel regime un pezzo che perde il contesto non diventa «non
verificabile»:

> **diventa una self-claim che nel testo originale non c'era.**

È un modo di sbagliare che quei lavori **non possono osservare**, perché nei loro
impianti c'è sempre una fonte contro cui misurare. È il ponte fra la loro
«over-decomposition» e il nostro L1: la tesi che ho portato al banco.

**Predizione depositata prima del banco** (msg `402605cc10e18db6`): sui 10 fatti veri
che devono restare ammessi, l'atomico ne ferma **almeno 2**.

---

## Che cosa questa lettura NON decide, e che va detto

- Nessuno dei cinque misura su **italiano**. Le nostre 15 e i nostri 60+60 sono in
  italiano, e lo splitter del lead è una regex sulle congiunzioni italiane: se cade,
  non cade la letteratura, cade quella regex. La distinzione va tenuta o si falsifica
  una tesi diversa da quella depositata.
- Nessuno misura il **costo per scrittura** in un sistema che scrive in linea: FActScore
  e successori sono metriche di valutazione *offline*, girano dopo. Da noi la
  decomposizione entrerebbe **nel percorso di scrittura**, e N claim atomici sono N
  giudizi. Quel numero non sta in nessuno di questi lavori: va misurato da noi, dentro
  un impianto solo.
- Ho letto **abstract e pagine HTML**, non i PDF interi (il 19,11% viene dal corpo
  dell'HTML di DnDScore). Chi vuole il dettaglio delle tabelle deve aprire i PDF.

---

*Nota di metodo, per chi legge il registro:* questa pagina sta in `docs/ricerca/` e non
in memoria. Ho lavorato per tutta la sessione in **sola lettura** sullo store di Aurelio
(`verimem save` mai eseguito): il vincolo non me lo tolgo da solo. Il contenuto è
comunque citabile e versionato, come la letteratura del 02/09
(`docs/ricerca/2026-09-02-muri-e-cure-letteratura.md`); chi ha il permesso di scrivere
può salvarlo con gli URL di questa tabella.
