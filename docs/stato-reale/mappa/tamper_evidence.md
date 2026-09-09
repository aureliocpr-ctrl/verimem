# Mappa di `verimem/tamper_evidence.py` — 10 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/tamper_evidence.py:31` `canonical_bytes` | funzione: Deterministic serialization of an entry: JSON with sorted keys, no incidental | `verimem/tamper_evidence.py:24`; `verimem/tamper_evidence.py:45`; `verimem/tamper_evidence.py:182` (+2) | nessuno | - | NON MISURATO | - |
| 2 | `verimem/tamper_evidence.py:39` `entry_hash` | funzione: ``sha256(prev_hash \|\| 0x00 \|\| canonical(entry))`` as hex. The domain-separator | `verimem/adjudication_log.py:29`; `verimem/adjudication_log.py:117`; `verimem/adjudication_log.py:140` (+33) | `tests/test_adjudication_log_chain.py`; `tests/test_adjudication_pins.py`; `tests/test_audit_mutations.py` (+2) | - | NON MISURATO | - |
| 3 | `verimem/tamper_evidence.py:49` `build_chain` | funzione: Running entry-hash after each entry: ``out[i]`` chains ``entries[0..i]``, so | `verimem/tamper_evidence.py:24` | `tests/test_tamper_evidence.py` | - | NON MISURATO | - |
| 4 | `verimem/tamper_evidence.py:61` `verify_chain` | funzione: Recompute the chain and return the index of the FIRST entry whose stored hash | `verimem/tamper_evidence.py:25` | `tests/test_tamper_evidence.py` | - | NON MISURATO | - |
| 5 | `verimem/tamper_evidence.py:93` `_require_crypto` | funzione: (nessun docstring) | `verimem/tamper_evidence.py:113`; `verimem/tamper_evidence.py:135`; `verimem/tamper_evidence.py:155` (+2) | nessuno | - | NON MISURATO | - |
| 6 | `verimem/tamper_evidence.py:107` `generate_audit_keypair` | funzione: Generate an ed25519 keypair for audit-head signing; returns | nessuno trovato | `tests/test_tamper_anchor_b.py`; `tests/test_tamper_anchor_receipt.py` | - | NON MISURATO | - |
| 7 | `verimem/tamper_evidence.py:131` `sign_head` | funzione: Sign a chain head with the operator's ed25519 private key; returns the | `verimem/audit_anchor.py:7`; `verimem/client.py:2677`; `verimem/client.py:2678` (+1) | `tests/test_tamper_anchor_b.py` | - | NON MISURATO | - |
| 8 | `verimem/tamper_evidence.py:142` `verify_head_signature` | funzione: True iff ``signature_b64`` is a valid signature of ``head_hash`` under | nessuno trovato | `tests/test_tamper_anchor_b.py` | - | NON MISURATO | - |
| 9 | `verimem/tamper_evidence.py:179` `sign_receipt` | funzione: Sign the canonical serialization of ``payload`` (the receipt WITHOUT its | `verimem/audit_anchor.py:15`; `verimem/audit_anchor.py:39`; `verimem/audit_anchor.py:110` (+1) | `tests/test_tamper_anchor_receipt.py` | - | NON MISURATO | - |
| 10 | `verimem/tamper_evidence.py:192` `verify_receipt_signature` | funzione: True iff ``signature_b64`` signs the canonical bytes of ``payload`` under | `verimem/audit_anchor.py:39`; `verimem/audit_anchor.py:165`; `verimem/tamper_evidence.py:151` | `tests/test_tamper_anchor_receipt.py` | - | NON MISURATO | - |

---

# 🔴 T48 — la testa è FIRMATA e quella firma non è MAI verificata

**Assegnato dal lead come T48.** ⚠️ Il lead lo indirizzava a `provenance_signing.md`: le
funzioni stanno **qui**, in `tamper_evidence.py` — verificato con
`grep -ln "def sign_head\|def verify_head_signature" verimem/*.py`. Scritto dove vive il
codice.

    funzione                    in tamper_evidence   altrove in verimem/   test
    sign_head                          1 (solo def)          4              1
    verify_head_signature              1 (solo def)          0   ⚠️         1
    sign_receipt                       2                     3              1
    verify_receipt_signature           2                     2   ✅         1

⇒ **Il prodotto appone la firma della testa in 4 punti e non la controlla mai.** Non è che
«non verifica niente»: `verify_receipt_signature` è chiamata da `client.audit_verify_anchor`
— *«Verify a signed anchor receipt …: signature valid, both chains intact, row counts only
grew»*. **L'asimmetria è fra due firme dello stesso file.**

## E sono due livelli distinti, non uno

    livello 1  catena di hash      client.audit_verify()    ✅ PROVATA da @ws3 rompendo la
                                                               catena: torna l'id della riga
                                                               manomessa
    livello 2  firma della testa   sign_head → verify_…     ⚠️ apposta, mai controllata

`mutation_audit` **non nomina mai** la firma: i due livelli non si toccano.

## 📌 E un terzo reperto, trovato indirizzando T48

`provenance_signing.py` ha **la sua coppia** `sign_ref` / `verify_ref`, più
`verify_fact_refs` e `audit_store`. E i due file **non si citano**:

    grep -c "provenance_signing" verimem/tamper_evidence.py  → 0
    grep -c "tamper_evidence" verimem/provenance_signing.py  → 0

⇒ **Nel prodotto convivono DUE sistemi di firma indipendenti che non si conoscono.** Non è
un difetto di per sé — possono avere scopi diversi — ma è il genere di cosa che chi legge
«firmato» deve sapere: **quale firma, apposta da chi, verificata da cosa.**

⛔ **Quello che T48 NON dice**: se sia sfruttabile. Nessun modello di minaccia qui, e la
firma della testa potrebbe servire a un verificatore **esterno** al prodotto.
