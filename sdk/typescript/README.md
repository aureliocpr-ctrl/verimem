# verimem-client (TypeScript)

Typed, zero-dependency client for the [Verimem](https://verimem.com)
trusted-memory gateway. Native `fetch` (Node ≥ 18, browsers, edge runtimes).
The API key travels only as an `Authorization` header — never in a URL.

```ts
import { VerimemClient } from "verimem-client";

const memory = new VerimemClient({
  baseUrl: "http://127.0.0.1:8377",
  apiKey: process.env.VERIMEM_KEY!,
});

// verified fact -> admitted
await memory.add("deploy pipeline is green", { verifiedBy: ["ci:main:green"] });

// unsupported hype -> quarantined by the gate (any language)
const r = await memory.add("the deployment works and is verified in production");
console.log(r.status); // "quarantined"

// recall with provenance / evidence dossier / trust odometer
const hits = await memory.search("deploy status");
const report = await memory.explain("deploy status");
const stats = await memory.stats(); // { trust: { ledger: { admitted, quarantined, ... } } }
```

Errors throw `VerimemError` with `.status` and the gateway's error body.

## Development

The contract test runs against a LIVE gateway and is orchestrated by the
Python suite (`tests/test_sdk_typescript.py` boots the gateway, provisions a
tenant, then runs `node --test`). Standalone:

```bash
VERIMEM_URL=http://127.0.0.1:8377 VERIMEM_KEY=vm_... npm test
npm run build   # emits dist/ for publishing
```
