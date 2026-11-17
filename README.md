# ZUKA AI Cybersecurity Assistant

A research SOC application with a React dashboard, FastAPI backend, PostgreSQL,
XGBoost detection, SHAP explanations, incident investigations, reports, and a
offline project knowledge assistant, with optional Ollama generation.

Detection uses **dataset replay**, not live packet capture. Defense actions record
simulated containment in the investigation ledger; they do not configure real
firewalls or quarantine devices.

## Status

The source repository is [public on GitHub](https://github.com/karthik-856/AI-Cybersecurity-Assistant). See
[the readiness review](docs/GITHUB_READINESS.md) for test results, remaining
quality/security findings, and the limits of verification. This is not a
production security appliance.

Live demonstration: [zuka-soc.onrender.com](https://zuka-soc.onrender.com).

[Free deployment instructions](docs/FREE_DEPLOYMENT.md) cover the complete
website/API on Render and a separate Neon PostgreSQL database. Free hosting can
sleep and has quotas; it does not provide an always-on production SLA.

## Local setup

Use Python 3.12, Node.js 22, and PostgreSQL 16 or later. Run commands from the
project root unless a different directory is shown.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
Copy-Item .env.example .env
```

Create an empty PostgreSQL database. Edit `.env` with its `DATABASE_URL`, a
generated `JWT_SECRET_KEY`, and a different generated `OTP_SECRET`. Never commit
`.env`, keys, account databases, or SMTP credentials. Leave replay disabled until
you want demonstration traffic.

```powershell
python -m scripts.init_database --admin-username admin --admin-email your-address@example.com
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The database initializer applies migrations, creates the three application roles,
and prompts privately for an administrator password. It never supplies a default
administrator password. In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. API documentation is at
`http://127.0.0.1:8000/docs`. The frontend uses a same-origin API proxy by default;
set `VITE_API_BASE_URL` at build time only when using a different API origin.

## Accounts and notifications

Public registration always creates a VIEWER. An administrator grants operational
roles through user management. Email verification, password recovery, and email
two-factor authentication require working SMTP settings. Web Push additionally
requires VAPID keys and an HTTPS deployment. Automated tests capture email in
memory; they never send real mail.

Existing bcrypt hashes remain supported. Plaintext password records are rejected
and require an administrator-assisted password reset. Password resets and changes
revoke existing sessions.

## Local knowledge assistant

For browser permission, background push setup, device tests, and free-host sleep
limits, see [the notification guide](docs/NOTIFICATIONS.md).

The default knowledge workflow uses local hashed text vectors and a SQLite index.
Reviewed project answers, record queries, and guided operations work without a
paid AI API or a model server. The index is built automatically when needed, or:

```powershell
python -m rag_assistant.ingest
```

Free deployment sets `ZUKA_LLM_PROVIDER=disabled` and
`RAG_GENERATION_ENABLED=false`. Unknown knowledge questions return a clear
fallback. For optional local generation, install Ollama separately, pull your
chosen model, and configure `ZUKA_OLLAMA_MODEL` / `CHAT_MODEL` and the appropriate
Ollama URL. Set `RAG_GENERATION_ENABLED=true` only when that server is available.
Chroma, external embeddings, and an external model download are not required.

## Model and datasets

The required runtime model is included as
`models/zuka_unified_xgboost/model.json.gz`. The backend loads this compressed
artifact directly when an uncompressed local model is absent. Container builds
convert it losslessly to an untracked UBJ artifact for lower startup memory.
Native CPU inference and TreeSHAP share one model and honor early stopping. Schema and label
metadata accompany it. `data/sample_replay.csv` contains five held-out rows from
each of the 13 documented classes for a small demonstration; it is not a
representative model evaluation dataset.

Large raw/processed research datasets, experimental model binaries, local
databases, and private presentation material are excluded. Existing local copies
are retained. Research notebooks and legacy scripts may require these external
artifacts; review their configured paths before running them. Dataset attribution:
CIC-IDS2017 from the Canadian Institute for Cybersecurity and UNSW-NB15 from UNSW
Canberra; consult the original providers' usage terms before redistribution.

## Tests

Create a **separate disposable PostgreSQL database** named `zuka_test_*`:

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg2://postgres:your_password@localhost:5432/zuka_test_local"
python -m pytest -q
cd frontend
npm run build
npm run lint
npm audit --audit-level=low
```

The test configuration refuses to run against the normal application database.
It applies migrations and creates test-only users. It covers authentication,
permissions, incident resolution, defense notes, report operations, assistant
dispatch, compressed model loading, SHAP, and replay. Ad hoc scripts outside the
configured pytest suite can depend on a running service or existing data and
must not be pointed at a real account database.

## Docker Compose

Set `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, and `OTP_SECRET` in `.env` before use.
Use a URL-safe database password, or URL-encode it where it appears in a database
URL. Then run `docker compose up --build`. A one-off migration service initializes
the schema before backend/replay services start. Create the initial administrator
with `docker compose run --rm backend python -m scripts.init_database
--admin-username admin --admin-email your-address@example.com` (one command).
The frontend is served on port 80; database/API ports bind to loopback.

GitHub Actions builds the production image, runs database/model/PDF/assistant
smoke checks with a 512 MiB memory limit, and runs desktop/mobile browser tests.
See the linked Actions run for the result of your exact commit. Real email/push
delivery, backup restoration, and deployment-specific operations require separate
validation. Authentication requests have persistent database-backed throttling.

## Team collaboration

See [CONTRIBUTING.md](CONTRIBUTING.md) for inviting teammates, branches, pull
requests, required checks, and keeping deployment secrets out of source control.
