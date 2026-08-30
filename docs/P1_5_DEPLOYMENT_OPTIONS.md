# P1.5 Deployment Options

Reviewed against official platform documentation on 2026-08-31. This is an
architecture review only; no account, price, service, domain, secret, disk, or
deployment was created.

## Decision

**Recommended: one paid Render Web Service with one persistent disk.** Serve
FastAPI, the static Web/PWA, and the single-user SQLite operational store from
one instance. Mount the disk below `/opt/render/project/src`, for example at
`/opt/render/project/src/data`, and set `DATABASE_URL` to the corresponding
SQLite file. This matches the current CPython/Uvicorn application with the
least code and operational change.

**Fallback: one Railway service with one mounted volume.** Railway documents
FastAPI deployment, persistent volumes, volume backups, secrets/variables,
custom domains, and deployment rollback. Use this only if Render service/disk
availability or account constraints make the recommended path unsuitable.

## Comparison

| Platform | Current fit | Persistent data | Cold start / runtime | Secrets, domain, rollback | Decision |
|---|---|---|---|---|---|
| Render | Direct FastAPI web service; one service also serves the PWA | Local filesystem is ephemeral by default. SQLite requires a paid service plus persistent disk; free web services cannot attach one. | Free services spin down after 15 minutes and can take about a minute to resume. Paid instances do not spin down. | Environment secrets, managed TLS/custom domains, health checks, and rollback are documented. A disk disables zero-downtime deploys. | **Recommended** |
| Railway | Direct FastAPI service | Mounted volumes persist SQLite and support manual/scheduled backups. | Actual latency/cold-start behavior depends on the selected plan and must be measured during acceptance. | Variables can be sealed; custom domains receive SSL; prior deployments can be rolled back within plan retention. | **Fallback** |
| Vercel | FastAPI is supported as a Python Function, currently documented as Beta | Function filesystem is read-only except ephemeral `/tmp`; current SQLite design would require an external database and architecture change. | Functions can be archived and incur a later first invocation; duration/bundle limits apply. Current supported Python versions also start above the repository's 3.9 baseline. | Strong domain/deployment features, but not enough to overcome the persistence mismatch. | Not selected |
| Cloudflare | Python Workers now support FastAPI, but Python Workers are Beta and use a Workers/Pyodide execution model | Current filesystem SQLite is not portable; migration to D1 or another binding would change storage and tests. | Edge runtime is attractive, but requires a Python 3.13/Workers packaging and application adaptation. | Workers secrets, custom domains, versions and rollback are documented. | Not selected |

## Recommended Render shape

```text
Internet HTTPS
-> Render Web Service (single instance)
   -> FastAPI API + static Web/PWA
   -> /opt/render/project/src/data/p1_5_capture.sqlite3
      on one persistent disk
```

Build command:

```bash
python -m pip install -e ".[hybrid]"
```

Start command concept:

```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port "$PORT"
```

Required production environment: `APP_ENV=production`, `AUTH_MODE=token`,
`API_AUTH_TOKEN` as a platform secret, explicit HTTPS `ALLOWED_ORIGINS`,
`AI_PROVIDER=mock` until live Gemini acceptance, and the disk-backed
`DATABASE_URL`.

`deploy/render-staging.yaml` encodes this initial MockProvider shape with one
instance, one 1 GB disk, `autoDeployTrigger: off`, runtime-generated auth token,
explicit operator-supplied CORS, and application-level rate limits enabled by
production mode. It is not synced. The selected Singapore region, paid plan,
current pricing, data location, and remotely available commit must be confirmed
before external setup.

## Persistence and rollback caveats

- A Render code rollback does not roll back disk state. Disk snapshots and
  application/database recovery are separate procedures.
- Render documents daily disk snapshots, but SQLite-consistent recovery must be
  tested with this application's write pattern before trusting it.
- A persistent disk is single-instance and prevents zero-downtime deploys. This
  is acceptable only for the single-user MVP.
- Free Render is suitable for a disposable demo with mock/nonessential data,
  not this SQLite operational store: restarts/redeploys/spin-down discard local
  changes.
- Railway volume backup restore is limited to the same project/environment and
  is described as a newer feature; restoration still needs an application-level
  acceptance test.

## Cost statement

No numeric cost is recorded because pricing can change and no account/region
was inspected. The recommended path is not free when SQLite persistence is
required. Confirm current service, disk, bandwidth, backup, and outbound API
charges immediately before deployment.

## Official sources

- [Render FastAPI/web service deployment](https://render.com/docs/your-first-deploy)
- [Render free-service limits](https://render.com/docs/free)
- [Render persistent disks](https://render.com/docs/disks)
- [Render deploys and rollback](https://render.com/docs/deploys)
- [Render Blueprint YAML reference](https://render.com/docs/blueprint-spec)
- [Render environment variables and secrets](https://render.com/docs/configure-environment-variables)
- [Render DDoS protection boundary](https://render.com/docs/ddos-protection)
- [Render Python version selection](https://render.com/docs/python-version)
- [Railway FastAPI guide](https://docs.railway.com/guides/fastapi)
- [Railway volumes and backups](https://docs.railway.com/volumes/backups)
- [Railway variables](https://docs.railway.com/variables)
- [Railway deployment actions](https://docs.railway.com/deployments/deployment-actions)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel runtime filesystem](https://vercel.com/docs/functions/runtimes)
- [Cloudflare Python Workers FastAPI](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/)
- [Cloudflare Workers versions](https://developers.cloudflare.com/workers/versions-and-deployments/)
