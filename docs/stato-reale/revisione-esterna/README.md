# Revisione esterna — il primo lettore ostile non-interno

> Mandato di Aurelio (30/08 sera): usare il credito z.ai con GLM-5.3 come
> critico esterno. Motivo dal report stesso (sez. 5, W2-72): «tutte le
> verifiche sono interne; un lettore ESTERNO non c'è ancora stato, e il
> registro dimostra di reggere noi, non lui».

## Round 1 — il report di stato (30/08, 20:40-20:47)

- **Revisore**: GLM-5.3 (`glm-5.3`, endpoint api.z.ai), nessun accesso al
  repo: SOLO il testo di `REPORT-30-08-lo-stato-vero-del-prodotto.md`,
  come qualunque lettore pubblico.
- **Tre lenti indipendenti** (design del critic-orchestrator adattato a
  documento): `glm53-round1-premortem.md` (l'analista che smonta il report)
  · `glm53-round1-perimetro.md` (errori di categoria, cosa manca) ·
  `glm53-round1-presidi.md` (i processi dichiarati possono scattare?).
- **Costo**: 11.281 token in ingresso, 32.863 in uscita, 3 chiamate.
- **Formato per finding**: (a) citazione incriminata · (b) perché non regge
  per un lettore esterno · (c) cosa chiederebbe per verificare.

## Primo esito verificato (stessa sera)

Il finding *presidi-2* (contraddizione fra sez. 1 «anti-eco entrata col
processo pieno» e sez. 2 «in attesa 2ª firma») era REALE: la 2ª firma non
era scritta in nessuna cella, quindi per la regola del registro non
esisteva, e la sez. 1 sopravvendeva. Chiuso dando la firma (LANT-103), non
riscrivendo la frase. Nello stesso finding-cluster: lo SHA `275648c0`
citato dal report era il pre-rebase del vivo `1a4b8635` — il finding-5 di
*presidi* («gli SHA citati non si possono dare per risolventi») aveva un
caso concreto.

Gli altri finding vanno trattati come le correzioni interne: ognuno o
produce una correzione nel registro/report, o una risposta motivata scritta
accanto al finding. Nessuno si archivia senza l'una o l'altra.
