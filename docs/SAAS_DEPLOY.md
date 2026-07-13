# Verimem SaaS — deploy & go-live runbook

The commercial layer is **code-complete and tested** (subscription tiers, quotas,
per-plan rate limits, usage/billing export). This runbook is the bridge from *"the
code is built"* to *"the managed service is live"*. Steps marked **[code ✓]** are done
and shipped; steps marked **[operator]** are infrastructure/account actions that must
be performed by a human with the accounts (they are deliberately NOT automated).

## What is built (code ✓)

- **One codebase, two business models.** The same gateway serves the classic
  **self-host** product (plan `self_host`, un-metered, every feature on) and the metered
  **SaaS** tiers — no fork. See `engram/gateway_plans.py`.
- **Tiers** `free` / `pro` / `enterprise` with enforced limits:
  | plan | facts | rate/min | doc size | features |
  |---|---|---|---|---|
  | free | 1 000 | 60 | 10 MB | — |
  | pro | 100 000 | 600 | 50 MB | source-trust, backups |
  | enterprise | ∞ | ∞ | 200 MB | + SSO, air-gap, priority |
- **Quota teeth**: `POST /v1/memories` returns **402** with the quota snapshot when a
  tenant is at its fact cap; rate limit follows the plan (most-restrictive wins).
- **Self-serve windows**: `GET /v1/quota` (plan + headroom), `GET /v1/usage`
  (per-day line items + period total — the numbers an invoice sums).
- **Operator tooling**: `verimem gateway keys create --tenant X --plan pro`; `keys list`
  shows tiers; `gateway backup` / `restore`; remote tenant provisioning via `/admin/*`.
- **Container**: `Dockerfile` (multi-stage, slim, loopback-by-default) +
  `docker-compose.gateway.yml` (named volume, healthcheck).

## 1 — Provision the host [operator]

A Linux VM (2 vCPU / 4 GB min; the e5 embedder wants RAM). The gateway keeps ALL state
(keys db, per-tenant stores, model cache) in one Docker volume — the container is
disposable, the volume is the asset. Back it up (`gateway backup`).

## 2 — Run the gateway [code ✓ / operator]

```bash
docker compose -f docker-compose.gateway.yml up -d --build
docker compose -f docker-compose.gateway.yml exec gateway \
  verimem gateway keys create --tenant acme --plan pro --data-dir /app/data/gateway
curl http://127.0.0.1:8377/v1/health
```

The gateway binds **loopback** and **never terminates TLS itself** (by design).

## 3 — TLS + DNS [operator]

- Point `api.verimem.com` (A record) at the host.
- Put a TLS reverse proxy in front (Caddy auto-TLS, or nginx + certbot) terminating
  HTTPS and forwarding to `127.0.0.1:8377`. The repo's site already has the
  omnex/nginx pattern (see the `verimem-site-hosting` notes).

## 4 — Billing [operator, reads code ✓]

The metering is done; the integration is a thin external worker YOU own:

1. Create the Stripe account + products matching the tiers (free/pro/enterprise).
2. A cron/worker reads each tenant's `GET /v1/usage?since=<period-start>` and reports
   usage (or just enforces the tier — the caps already bite in-process).
3. On plan change, re-issue the tenant's key with the new `--plan` (or add an admin
   endpoint to update it — a small follow-up).

Stripe keys/webhooks are secrets: they live in the operator's environment, never in
this repo.

## 5 — Go-live checklist [operator]

- [ ] Volume backed up + a `gateway backup` cron.
- [ ] TLS valid on `api.verimem.com`, HTTP→HTTPS redirect.
- [ ] Admin key set (`--admin-key`) for `/admin/*`, kept out of client reach.
- [ ] Rate limit + body limit sane for the tier mix.
- [ ] A smoke test from a clean client (the TypeScript SDK contract test:
      `VERIMEM_URL=… VERIMEM_KEY=… npm test` in `sdk/typescript`).
- [ ] Monitoring on `/v1/health` + disk (the model cache + tenant stores grow).

## Honest status

The **product and the commercial layer are built and tested**; a managed cloud does not
exist until the **[operator]** steps above are done. Nothing here claims uptime,
adoption, or third-party audit. Ship it dark, watch the metering, then talk numbers.
