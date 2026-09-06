# Tre vie per il giudice v3.2 senza dilavare l'astensione — e dove il disegno può mentire

**ws3 «Galileo» · 05/09/2026 22:50 · letto PRIMA del banco di Nadia** (mandato: lead
`ea7c2ca3014b5a1c`, ordine di Aurelio 22:37 `9d8cb57161017947`; scadenza 23:15).

Il risultato di Nadia che cambia la strada: «più dati della stessa forma» è morta (400
astensioni in più → **28/100** sbagliate contro **9/100** del v3.1); il braccio a
etichette casuali (30/100) dice che la scorciatoia non è nei dati — **è il fine-tune che
dilava la capacità di astenersi del base**; la separazione fra le classi è dei dati
(+0,171 col rumore al 22% contro +0,763). La domanda: *come si tiene la separazione (dei
dati) senza dilavare l'astensione (del base)?*

---

## Le tre vie, con l'URL e ciò che ognuna promette davvero

| via | lavoro | URL | che cosa dice, e a che condizione |
|---|---|---|---|
| **(a) interpolazione dei pesi** | **WiSE-FT** — Wortsman, Ilharco et al., CVPR 2022 | https://arxiv.org/abs/2109.01903 · https://github.com/mlfoundations/wise-ft | pesi finali = α·Φ_fine-tuned + (1−α)·Φ_zero-shot. Su ImageNet + 5 shift: +4–6 punti sotto shift e +1,6 in-distribution, **a costo zero** in training e inferenza. Condizione implicita: **le due reti hanno la stessa forma**, testa compresa (CLIP zero-shot ha già la testa «da testo»). |
| **(a′) media di pesi** | **Model soups** — Wortsman et al., ICML 2022 | https://arxiv.org/abs/2203.05482 | media di più fine-tune migliora ID e OOD senza costo d'inferenza. **Limite dichiarato in letteratura**: i soups *non* garantiscono di conservare la **calibrazione** (la conservano «solo approssimativamente»), mentre gli ensemble sì. |
| **(b) vincolo verso il base** | **L2-SP** — Li, Grandvalet, Davoine, ICML 2018 | https://arxiv.org/abs/1802.01483 | penalità L2 verso i pesi *pre-addestrati* invece che verso zero: dimentica meno. |
| | **Mixout** — Lee, Cho, Kang, ICLR 2020 | https://arxiv.org/abs/1909.11299 | «un regolarizzatore L² *adattivo* verso i pesi pre-addestrati»: a ogni passo alcuni parametri tornano al base. |
| | **LoRA** — Hu et al., 2021 | https://arxiv.org/abs/2106.09685 | aggiornamenti a basso rango; **ma** «le strategie parametro-efficienti come LoRA soffrono ancora di dimenticanza catastrofica» (Scaling laws for forgetting, https://arxiv.org/abs/2401.05605): basso rango ≠ nessun dilavamento. |
| **(c) cascata** | il v3.2 decide la separazione, il **base** decide l'astensione | design 0.8.0, pagina (b) | conserva l'astensione *per costruzione*: la classe `neutral` della testa NLI del base resta intatta perché il base non viene toccato. Costo: due modelli (o due teste) per scrittura. |

---

## 🔴 La falsificazione del DISEGNO, prima che il banco giri

Non è «la tesi è falsa»: è *dove il banco può mentire anche se la tesi fosse vera*.

### F1 — WiSE-FT qui **non è definito sulla testa**, e l'astensione vive nella testa
Dal codice, non dedotto (`verimem/local_grounding.py:6-7, 183-190, 565`):
- base = `cross-encoder/nli-deberta-v3-base` → testa **a tre classi** (contradiction /
  entailment / **neutral**);
- v3.x = «cross-encoder fine-tuned … **with a binary head**: sigmoid(logit)·100».

α·Φ_ft + (1−α)·Φ_base è calcolabile **solo sul corpo DeBERTa**; le due teste hanno forme
diverse (1 logit contro 3) e non si sommano. Quindi «WiSE-FT a α = 0,25/0,5/0,75» va
**specificato**, e le tre specifiche danno risposte diverse:
- **(α) corpo interpolato + testa binaria del v3.2** — è la lettura più naturale, ma
  l'astensione del base *non c'è* in quella testa: è stata sostituita. Se il dilavamento
  è nella testa (e la testa binaria è ciò che il fine-tune ha *creato*), questa variante
  non può riportare le 28/100 a 9/100 **per costruzione**, qualunque α.
- **(β) corpo interpolato + testa NLI del base** — il punteggio torna a essere
  P(entailment) o (entailment − contradiction), con `neutral` come astensione. È di
  fatto un giudice NLI *con il corpo un po' spostato*: è la stessa famiglia dei miei
  scorer A/B/C di ieri, non «il v3.2 riparato».
- **(γ)** = la cascata (c), che non interpola nulla.
⇒ **Predizione mia, depositata qui, prima che Nadia esegua**: la variante (α) non
riporta le astensioni sotto 9/100 a *nessun* α (muore se lo fa: allora il dilavamento
era nel corpo, e la tesi del lead è più forte); la variante (β) le riporta ma perde il
divario del v3.2 più di quanto la tesi conceda (< +0,40) (muore se tiene ≥ +0,53).
Il banco deve **dichiarare quale variante** gira, o il numero non ha un'interpretazione.

### F2 — l'astensione è **calibrazione**, e la media di pesi non la conserva
«Astenersi» = una soglia su un punteggio. La letteratura dei soups dice esplicitamente
che l'averaging *non garantisce* la calibrazione dei costituenti. Quindi il criterio «le
astensioni sbagliate tornano sotto 9/100» va misurato **a soglia ricalibrata** per ogni
α, non alla soglia del v3.2: altrimenti si confronta un modello alla sua soglia con un
modello a una soglia altrui, e il 9/100 può apparire o sparire spostando il cut.

### F3 — «≥ 70% del divario» su **n = 100** non è decidibile senza intervallo
28/100 contro 9/100 si decide (Wilson non si sovrappone). «Divario ≥ +0,53 contro
+0,763» su 100 esempi ha un errore standard che un bootstrap deve mostrare; e il
confronto fra α va fatto **appaiato** sugli stessi esempi (come il mio `differenza` di
ieri), non su medie separate.

### F4 — un dato già in casa che il disegno deve usare
Ieri (`f3907dd9`, P3) ho misurato **proprio il base** (`cross-encoder/nli-deberta-v3-base`
= scorer A) contro il v3.x (R) sulle 30 contraddizioni implicite: **non distinguibili**
(intervallo appaiato che include lo zero). Cioè sulle implicite «l'astensione del base»
non è meglio del fine-tuned. I controlli di Nadia sono altri (i suoi 100), e il numero
non si trasferisce; ma un disegno che assume «il base si astiene bene» deve dirlo su
*quella* popolazione, con quel numero accanto.

---

## Che cosa consiglio al disegno (non al verdetto)

1. Dichiarare la variante: (α), (β) o (γ). Se il tempo è poco, **(β) e (γ) sono le uniche
   due in cui l'astensione del base esiste ancora**.
2. Per ogni α: **ricalibrare la soglia** sul set di calibrazione del v3.2, poi contare le
   astensioni sbagliate; riportare la soglia usata.
3. Confronto **appaiato** con bootstrap (1.000 ricampionamenti) su divario e astensioni.
4. Mettere accanto il mio A-contro-R di ieri sulle implicite, così il lettore sa che
   «il base si astiene» non è vero ovunque.

*Store di Aurelio in sola lettura; questa pagina sta in `docs/ricerca/` con gli URL.*
