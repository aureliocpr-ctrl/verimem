# TrustMem-Bench — il benchmark che imponiamo noi (design v0, 2026-07-06)

**Perché.** Oggi corriamo sulle piste altrui (HaluMem è del gruppo MemOS; LoCoMo/
LongMemEval misurano accuratezza grezza). Nessun benchmark pubblico misura ciò
che rende una memoria *affidabile*. Chi definisce il metro vince la categoria:
i competitor dovranno o ignorarlo (e la domanda "perché non lo passate?" resta)
o correrci — in casa nostra.

**Il problema di credibilità (dichiarato).** Un benchmark scritto dal venditore
è giudice-e-giuria. Mitigazioni non negoziabili:
1. **Riproducibile al 100%**: harness open, task generati da script con seed
   pubblicati, prompt del giudice pubblicati, un comando per rifare tutto.
2. **Anche i NOSTRI fallimenti nel report** (un autore che si dà 100/100 non è
   credibile — pubblichiamo il nostro punteggio VERO, buchi inclusi).
3. **Giudice duale**: check deterministici locali dove possibile (astensione,
   resurrezione post-delete, supersede sbagliati = misurabili senza LLM);
   giudice LLM solo dove serve semantica, con prompt versionati.
4. Inviti espliciti a terzi + PR di risultati accettate.

## I 6 assi (ognuno già prototipato dal nostro lavoro interno)

| Asse | Domanda | Metrica | Nostro precedente |
|---|---|---|---|
| 1. Fabrication under absence | la risposta NON è in memoria: inventa? | abstention-rate | Boundary 1.000/0.976 |
| 2. Sycophancy resistance | l'utente contraddice con insistenza un fatto evidenziato: cede? | cave-rate sotto pressione crescente | 1.0→0.0 col gate |
| 3. Destructive-update resistance | update con trappole cross-attributo: cancella fatti innocenti? | wrongful-supersede rate | dial 99→7, 0 cross-attr |
| 4. Temporal integrity | "quanto era X a marzo?" / "da quando è Y?" | as-of accuracy + transition accuracy | as_of + storia (+16pp) |
| 5. Forget integrity (GDPR) | dopo il delete, il dato risorge da QUALSIASI via? | resurrection-rate su deep/as-of/history/search | purge-chain (fix d0a8863) |
| 6. Provenance honesty | sa dire COME lo sa? | dossier presente + campi verificabili | TrustReport |

## Dataset
Generatore sintetico multi-sessione (personas con timeline, update, trappole)
— stile HaluMem ma NOSTRO: script + seed fissi, umanamente auditabile, EN + **IT**
(nessun benchmark memoria esiste in italiano: prima mossa anche lì). Taglie:
smoke (5 personas) / full (50). Zero dati reali = zero privacy.

## Esecuzione competitor (onestà operativa)
- **Verimem**: harness nativo.
- **mem0 OSS**: adapter locale; config LLM dichiarata (non la loro default
  OpenAI — caveat esplicito nel report; invito a submitarci il run ufficiale).
- **Zep/servizi**: se non eseguibili localmente, riga "not run — invited" (non
  numeri inventati). Il vuoto parla da solo.

## Roadmap
v0 design (questo doc) → generatore+smoke-set (locale) → run Verimem (pubblico,
con fallimenti) → adapter mem0 + invito pubblico → leaderboard nel repo.
Gate: dopo la chiusura dei binari correnti (e2e + review 5-lenti) e review del
design da parte di Aurelio.
