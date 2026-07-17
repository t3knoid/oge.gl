 ol

cd

# oge.gl Admin Guide

This guide covers runtime administration for oge.gl, including backend configuration, logging, and deployment workflows.

## Configuration

The backend loads configuration from `config/default.toml` by default.

Override precedence:

1. explicit `Settings(...)` init values
2. environment variables
3. config file values from `APP_CONFIG_FILE` when set, otherwise `config/default.toml`
4. dotenv values
5. file secret values

Environment variables override matching config-file keys.

`DATABASE_URL` values using Fly- or platform-style `postgres://...` or driverless `postgresql://...` PostgreSQL URLs are normalized to `postgresql+psycopg://...` at startup so SQLAlchemy uses the installed `psycopg` driver.

### Configuration Reference

| Setting                                                                           | Default                                                       | Type         | Allowed values                                            |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------- | ------------ | --------------------------------------------------------- |
| `APP_NAME` (`app_name`)                                                       | `oge.gl API`                                                | string       | any non-empty string                                      |
| `APP_VERSION` (`app_version`)                                                 | `0.1.0`                                                     | string       | semantic version string                                   |
| `API_V1_PREFIX` (`api_v1_prefix`)                                             | `/api/v1`                                                   | string       | path prefix string                                        |
| `DATABASE_URL` (`database_url`)                                               | `postgresql+psycopg://postgres:postgres@localhost:5432/oge` | string       | valid SQLAlchemy URL                                      |
| `OGE_BASE_URL` (`oge_base_url`)                                               | OGE disclosures collection URL                                | string       | valid absolute URL                                        |
| `SCRAPER_REQUEST_TIMEOUT` (`scraper_request_timeout`)                         | `30.0`                                                      | float        | positive float                                            |
| `INGEST_WORKER_POLL_INTERVAL_SECONDS` (`ingest_worker_poll_interval_seconds`) | `15.0`                                                      | float        | positive float                                            |
| `INGEST_WORKER_MAX_JOBS_PER_RUN` (`ingest_worker_max_jobs_per_run`)           | `10`                                                        | integer      | positive integer                                          |
| `RUNTIME_ENVIRONMENT` (`runtime_environment`)                                 | `local`                                                     | enum         | `local`, `non_local`                                  |
| `LOG_LEVEL` (`log_level`)                                                     | `INFO`                                                      | string       | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` (`log_format`)                                                   | `auto`                                                      | enum         | `auto`, `json`, `text`                              |
| `LOG_ENABLE_ROW_DEBUG` (`log_enable_row_debug`)                               | `false`                                                     | boolean      | `true`, `false`                                       |
| `LOG_FILE_PATH` (`log_file_path`)                                             | `/var/log/oge.gl/backend.log`                               | string       | writable file path                                        |
| `CORS_ALLOW_ORIGINS` (`cors_allow_origins`)                                   | `http://127.0.0.1:5173`, `http://localhost:5173`          | list[string] | valid origin URLs                                         |
| `APP_CONFIG_FILE`                                                               | `config/default.toml`                                       | string       | readable TOML file path                                   |

Use environment variables for secrets and environment-specific values instead of committing secret values in config files.

### Frontend Manual Fetch Defaults

The frontend manual fetch control uses backend-owned configuration values exposed through the ingestion API.

| Setting                                                           | Default         | Type    | Allowed values              |
| ----------------------------------------------------------------- | --------------- | ------- | --------------------------- |
| `MANUAL_INGEST_DEFAULT_MODE` (`manual_ingest_default_mode`)   | `incremental` | string  | `incremental`             |
| `MANUAL_INGEST_DEFAULT_LIMIT` (`manual_ingest_default_limit`) | `1`           | integer | integer from`1` to `25` |
| `MANUAL_INGEST_MAX_LIMIT` (`manual_ingest_max_limit`)         | `25`          | integer | integer`>= 1`             |

The frontend reads the effective values through `GET /api/v1/ingest/defaults`.
If backend configuration is invalid, startup should fail safely before the frontend receives a malformed defaults payload.
If the defaults API surface is unavailable, the UI should fail safely without submitting a malformed ingestion request.

## Logging

Backend logging behavior:

- API and worker processes use centralized logging configuration.
- `LOG_FORMAT=auto` uses text logs in local runtime and JSON logs in non-local runtime.
- Request identifiers are used as log correlation context after safe header normalization.
- API request failures emit structured log events with request context.
- Ingestion lifecycle logs include job-scoped context where available.
- Row-level parser diagnostics emit only when `LOG_ENABLE_ROW_DEBUG=true` and `LOG_LEVEL=DEBUG`.
- Local runtime writes logs to `LOG_FILE_PATH` and also emits to process output.
- If `LOG_FILE_PATH` is unavailable in local runtime, logs fall back to `/tmp/oge.gl/backend.log` with a warning event.

### Configuration Verification Commands

```bash
cd /path/to/oge.gl
source .venv/bin/activate

# File-backed defaults
python -c "from app.core.config import settings; print(settings.log_level, settings.api_v1_prefix)"

# Environment overrides
LOG_LEVEL=DEBUG API_V1_PREFIX=/api/custom python -c "from app.core.config import Settings; s=Settings(); print(s.log_level, s.api_v1_prefix)"
```

## Deployment

### Local Deployment Quick Start

This quick start deploys oge.gl from a source checkout.

1. Clone the repository.

```bash
git clone https://github.com/t3knoid/oge.gl.git
cd oge.gl
```

2. Deploy PostgreSQL.

```bash
docker run --name oge-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=oge \
  -p 5432:5432 \
  -d postgres:16
```

3. Prepare backend and run migrations.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/oge"
export OGE_BASE_URL="https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm"
export LOG_LEVEL="INFO"
export LOG_FORMAT="auto"
export RUNTIME_ENVIRONMENT="local"
export LOG_FILE_PATH="/var/log/oge.gl/backend.log"
export LOG_ENABLE_ROW_DEBUG="false"
export APP_CONFIG_FILE="config/default.toml"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Seed ingestion and verify.

```bash
source .venv/bin/activate
curl -sS -X POST "http://127.0.0.1:8000/api/v1/ingest/run" \
  -H "Content-Type: application/json" \
  -d '{"mode":"incremental","limit":1}'
curl -sS "http://127.0.0.1:8000/api/v1/ingest/jobs"
```

5. Optional frontend shell.

```bash
cd frontend
npm install
npm run dev
```

Optional backend overrides for manual fetch defaults:

```bash
export MANUAL_INGEST_DEFAULT_MODE="incremental"
export MANUAL_INGEST_DEFAULT_LIMIT="1"
export MANUAL_INGEST_MAX_LIMIT="25"
```

Open `http://127.0.0.1:5173` for UI verification.

### Managed Cloud Deployment (Fly.io + Supabase + Cloudflare)

This deployment path keeps a single-origin serving model in production.

Production serving model:

- Supabase provides the PostgreSQL database.
- Fly.io runs the container image built from the repository root `Dockerfile`.
- FastAPI serves both the compiled React frontend and the JSON API from the same public origin.
- Cloudflare fronts the public hostname for DNS, TLS, proxying, and WAF controls.
- The deployed frontend calls the colocated API through `/api/v1`.

#### Prerequisites

Create or confirm these operator prerequisites before deployment:

- a Supabase project with PostgreSQL access
- a Fly.io account with `flyctl` installed
- a Cloudflare zone for `oge.gl`
- repository access to build and deploy the current branch

Verify the Fly CLI is installed and authenticated:

```bash
fly version
fly auth login
```

#### Provision Supabase PostgreSQL

1. Create the Supabase project that will hold the production database.
2. Keep the database region close to the chosen Fly region when practical.
3. Copy the PostgreSQL connection string for application use.
4. Ensure the connection string includes SSL behavior. If assembled manually, keep `sslmode=require`.
5. Keep the database URL only in operator secret storage. Do not commit it to tracked files.
6. Prefer the direct Supabase connection string when the Fly runtime supports it. If IPv4 compatibility is required, use the Supavisor session-mode URL instead of transaction mode.

If the managed database provider returns a bare `postgres://...` or `postgresql://...` URL, it can be used directly. The backend normalizes that value to the `psycopg` SQLAlchemy driver during startup and release-time migrations.

#### Create The Fly.io App

Initialize the Fly app from the repository root without changing the application architecture.

```bash
cd /path/to/oge.gl
fly launch --no-deploy
```

Recommended Fly launch choices:

- app name: choose the production app name you intend to keep stable
- region: choose the closest practical region to the Supabase database
- database: do not provision Fly Postgres for this deployment path

Confirm the generated Fly configuration matches the container behavior:

- `internal_port = 8000`
- `release_command = "python -m alembic upgrade head"`
- HTTP and HTTPS handlers remain enabled for the public service
- the root `Dockerfile` is used for builds

The Fly image builds the React frontend and serves it from the same FastAPI process. The deployed site root serves the frontend shell and the frontend calls the colocated API through `/api/v1`.

#### Configure Production Runtime Settings On Fly.io

Store production settings in Fly secrets rather than tracked files.

```bash
fly secrets set \
  DATABASE_URL='REPLACE_WITH_SUPABASE_URL' \
  API_HOST='0.0.0.0' \
  API_PORT='8000' \
  OGE_BASE_URL='https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm' \
  LOG_LEVEL='INFO' \
  LOG_FORMAT='json' \
  RUNTIME_ENVIRONMENT='non_local' \
  SCRAPER_REQUEST_TIMEOUT='30' \
  PDF_STORAGE_DIR='/data/pdfs'
```

Production guidance for the key runtime values:

- `DATABASE_URL` must use the Supabase PostgreSQL connection string with SSL enabled.
- `API_HOST` and `API_PORT` should remain aligned with the container bind target `0.0.0.0:8000`.
- `LOG_FORMAT=json` and `RUNTIME_ENVIRONMENT=non_local` keep logs suitable for cloud aggregation.
- `PDF_STORAGE_DIR=/data/pdfs` should remain on the mounted writable data path.

#### Configure Cloudflare For The Public Hostname

Cloudflare remains the public edge in front of Fly.io.

DNS and proxy setup:

1. Create or update proxied DNS records for `oge.gl` that route traffic to the Fly app.
2. If you keep a `www` hostname, either proxy it to the same Fly app or configure a Cloudflare redirect to the canonical host.
3. Keep the Cloudflare orange-cloud proxy enabled for the public hostname.

Cloudflare origin certificate setup:

1. Open `SSL/TLS -> Origin Server` in Cloudflare for the target zone.
2. Click `Create Certificate`.
3. Use these certificate settings:

- private key type: `RSA (2048)`
- hostnames: `oge.gl` and `*.oge.gl` when a wildcard is appropriate
- certificate validity: `15 years`

4. Copy both the origin certificate and private key immediately. Cloudflare shows the private key only once.
5. Save the origin certificate as `origin-cert.pem` and the private key as `origin-key.pem` in a secure local operator workspace.
6. Add the custom domain to the Fly app if it is not already present.

```bash
fly certs add oge.gl -a oge-gl
```

7. Import the Cloudflare origin certificate and private key into Fly.

```bash
fly certs import oge.gl \
  --fullchain origin-cert.pem \
  --private-key origin-key.pem \
  --app oge-gl
```

8. Verify the imported certificate before validating strict TLS through Cloudflare.

```bash
fly certs check oge.gl --app oge-gl
```

TLS and edge settings:

- use Cloudflare SSL mode `Full (strict)`
- keep automatic HTTPS redirection enabled at the edge
- keep HSTS and related browser-hardening settings aligned with your broader domain policy
- treat the Fly hostname as an operator endpoint rather than the public product URL

WAF and abuse-control guidance:

- enable Cloudflare managed WAF rules for the public hostname
- use Cloudflare rate limits only as an edge complement, not as a replacement for application-level protections
- avoid trusting arbitrary forwarded client metadata unless you have verified the direct proxy CIDRs that actually connect to Fly

#### Deploy The Application

Deploy the current application image to Fly.io from the repository root.

```bash
cd /path/to/oge.gl
fly deploy
```

The root `fly.toml` runs `python -m alembic upgrade head` as a Fly release command during deploy, so schema migrations are applied before the new app version serves traffic.

After the first successful deploy, confirm the app is healthy:

```bash
fly status
fly logs
```

#### Scale Worker Capacity

Scale the API and worker processes after the first successful deploy.

```bash
fly scale count app=1 worker=1
```

#### Post-Deploy Verification

Run these checks after the first deploy and after every production update.

Edge and API checks:

```bash
curl -I https://oge.gl/
curl -i https://oge.gl/api/v1/health
curl -i "https://oge.gl/api/v1/transactions?page=1&page_size=5"
curl -i https://oge.gl/api/v1/ingest/jobs
```

Browser and functional checks:

- open `https://oge.gl/` and confirm the React frontend loads without a separate Vite server
- confirm the search UI renders and issues API requests against `/api/v1`
- verify a transaction result links to the source PDF provided by the backend
- submit a manual fetch and confirm the ingestion job is accepted and visible through the UI or API

#### Common Production Issues

The Fly deployment is healthy but the site is unreachable:

- confirm Cloudflare DNS records point to the correct Fly target
- confirm Cloudflare proxying is enabled for the public hostname
- confirm Cloudflare TLS mode remains `Full (strict)`

Database connectivity fails after deploy:

- confirm `DATABASE_URL` matches the current Supabase connection string
- confirm SSL remains enabled in the database URL
- confirm the Fly region and Supabase region are not introducing avoidable latency or firewall mismatches

Migrations fail during rollout:

- confirm the release image includes the expected Alembic revisions
- confirm `python -m alembic upgrade head` is running against the intended production database
- stop the rollout and resolve the schema issue before retrying the deploy

For architecture and local development requirements, see [docs/development-requirements.md](development-requirements.md).
For product behavior and API expectations, see [docs/product-specification.md](product-specification.md).
