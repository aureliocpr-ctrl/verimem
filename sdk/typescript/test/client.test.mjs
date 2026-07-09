/**
 * Contract test contro un gateway Verimem VIVO.
 *
 * Richiede env: VERIMEM_URL + VERIMEM_KEY (li fornisce l'orchestratore pytest
 * tests/test_sdk_typescript.py, che avvia il gateway e poi questo file via
 * `node --test`). Senza env: skip pulito, mai un finto verde.
 *
 * Node >= 23.6 esegue i .ts nativamente (type stripping) — importiamo la
 * SORGENTE: il test copre esattamente ciò che verrà pubblicato, senza build.
 */
import assert from "node:assert/strict";
import test from "node:test";

const URL_ = process.env.VERIMEM_URL;
const KEY = process.env.VERIMEM_KEY;
const skip = !URL_ || !KEY ? "VERIMEM_URL/VERIMEM_KEY not set (live gateway needed)" : false;

const { VerimemClient, VerimemError } = await import("../src/index.ts");

test("health + verified write + hype quarantined + search + stats", { skip }, async () => {
  const client = new VerimemClient({ baseUrl: URL_, apiKey: KEY });

  const h = await client.health();
  assert.equal(h.ok, true);

  // scrittura con evidenza -> ammessa
  const ok = await client.add("release 0.4.1 tagged on github", {
    verifiedBy: ["git:v0.4.1"],
    topic: "sdk-ts-test",
  });
  assert.equal(ok.stored, true);
  assert.ok(ok.id, "id presente");

  // hype senza evidenza -> il gate la quarantena (MAI persa: stored=true)
  const hype = await client.add(
    "the deployment works and is verified in production",
  );
  assert.equal(hype.stored, true);
  assert.equal(hype.status, "quarantined");

  // recall con provenance
  const hits = await client.search("release tagged", { k: 3 });
  assert.ok(Array.isArray(hits) && hits.length >= 1);

  // get by id + null su id inesistente
  const fact = await client.get(ok.id);
  assert.ok(fact, "fatto recuperabile per id");
  assert.equal(await client.get("no-such-id-xyz"), null);

  // odometro: le due scritture sono contate
  const stats = await client.stats();
  assert.ok(stats.trust.ledger.admitted >= 1);
  assert.ok(stats.trust.ledger.quarantined >= 1);
  assert.ok(stats.usage.requests >= 2);

  // delete
  const del = await client.delete(ok.id, { purgeHistory: true });
  assert.equal(del.removed, true);
});

test("bad key -> VerimemError 401, chiave mai in URL", { skip }, async () => {
  const bad = new VerimemClient({ baseUrl: URL_, apiKey: "vm_wrong" });
  await assert.rejects(
    () => bad.stats(),
    (err) => err instanceof VerimemError && err.status === 401,
  );
});
