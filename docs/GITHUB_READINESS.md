# GitHub readiness review — 16 November 2026

**Current review:** the repository is public. Production hardening and free-tier
deployment verification are in progress; the original findings below are
retained as historical context until the final checks complete. Test success is not
a claim that every possible operation, deployment, or attack scenario was tested.

## Current hardening changes

- Frontend lint now passes with zero warnings allowed; the original 78 errors
  and seven warnings were fixed without disabling the rules. Production builds
  pass. Browser/container CI now checks desktop and mobile routes.
- Chroma was replaced by a local SQLite knowledge index with deterministic text
  vectors. Reviewed knowledge answers and database operations need no external
  model. Unknown questions return a fallback; optional generation is disabled in
  the free deployment configuration.
- Production authentication has persistent, atomic PostgreSQL throttling.
  Logout revokes the server session. Push destinations are restricted and a
  subscription cannot be reassigned to a different user.
- Production secrets are validated, API responses are not cached, security
  headers are applied, and the built website and API share one origin.
- Fabricated reports and default containment/escalation claims were removed.
  UI text distinguishes replay data and recorded defense plans from external
  device enforcement. All roles can manage their own Settings.
- Native CPU inference and TreeSHAP share the loaded model. An independent
  comparison against XGBClassifier matched all 845 probabilities across the
  65-row sample exactly after preserving early stopping.
- The current installed Python dependency audit reports zero known advisories.
  A container build and browser run with a 512 MiB limit are required before
  accepting the free-server configuration. Cloud publication is also blocked
  until the hosting/database account connections work.

## Original publication results (superseded where noted above)

- Backend: **171 tests passed**, zero failures/skips, in 168.62 seconds on
  Windows/Python 3.12 with an isolated PostgreSQL 18 database. There were 217
  warnings, primarily deprecated naive UTC timestamp helpers.
- Authentication checks cover every API operation marked as protected in the
  OpenAPI schema. Functional cases include login, email verification, email
  two-factor login, password recovery/reuse rejection, session revocation,
  role checks, database record redaction, defense notes, reports/PDF, incident
  resolution rules, and assistant command parsing/database responses.
- The compressed production model loads independently of the excluded raw
  model. Predictions execute on examples from all 13 sample classes. SHAP and
  replay execute successfully. These are functional checks, not a new accuracy
  or robustness evaluation.
- Database migrations apply on an empty database. `alembic check` detects no
  missing schema changes. All installed Python dependencies are compatible.
- Python syntax parsed successfully for 157 application/research script files.
- Frontend TypeScript/production build passes after dependency updates.
- Live local knowledge integration: 53 chunks indexed into a disposable Chroma
  store; two project/workflow questions answered with knowledge sources; an
  unrelated question returned the expected fallback. Models used:
  `qwen2.5:3b` and `nomic-embed-text` on local Ollama. Three questions are a smoke
  test, not an exhaustive assistant quality evaluation.
- npm production dependency audit: **zero known advisories** in the checked
  installed versions. Compatible updates removed all four originally reported
  high-severity frontend advisories.

## Fixes made before publication

- Removed plaintext password fallback, added long-password-safe hashing while
  retaining existing bcrypt hash compatibility, and revoked active sessions on
  password changes/resets.
- Public registration grants VIEWER only. Privileged roles require administrator
  assignment. Added operational role checks to defense, report mutations,
  prediction, and replay.
- Defense mutations validate that the incident exists, the investigation belongs
  to that incident, and the investigation is still open.
- Redacted OTP hashes, session identifiers, and push secrets in Database Center.
- Replaced flagged `python-jose`/`ecdsa` dependencies with PyJWT and locked the
  Python dependency graph for reproducible installations.
- Added the missing reports table and investigation workspace migration.
- Replaced hardcoded browser API loopback URLs with configurable same-origin
  requests. Fixed container dependency installation for its unprivileged user,
  included runtime modules, required configured secrets, added migration startup,
  and corrected optional Ollama configuration.
- Packaged the required runtime model below GitHub's file-size limit and added
  a 65-row demonstration dataset. Large research artifacts and local account
  data remain on the original computer.
- Added a README, isolated test safeguards, and GitHub Actions checks for backend
  tests, frontend builds, and production frontend dependency advisories.

## Original findings and remaining verification

1. **Resolved — frontend lint:** originally 78 errors and 7 warnings. Findings included effect/state
   handling, hook dependencies, render purity, loose types, empty handlers, and
   fast-refresh boundaries. These were reported rather than silenced or globally
   disabled. CI currently checks compilation/tests, not lint acceptance.
2. **Resolved — development dependencies:** npm originally reported seven moderate advisories in the
   TypeScript ESLint/minimatch development toolchain. The offered automatic fix
   changes the declared toolchain incompatibly, so it was not forced.
3. **Resolved by removal — Chroma:** the original Python audit reported five entries representing
   four unique advisories against ChromaDB 1.5.9: PYSEC-2026-311,
   PYSEC-2026-3814, PYSEC-2026-3815, and PYSEC-2026-3813. The audit lists no fixed
   versions. These concern Chroma server authorization/code execution. This
   application uses an embedded persistent client and exposes no Chroma HTTP
   service, but that narrower use does not establish production safety. Recheck
   upstream fixes or replace the dependency before approving a deployment.
4. Docker was unavailable on the review machine. Container changes were inspected
   and configuration parsed, but images were not built or started locally.
5. Real SMTP email delivery, real browser/OS push delivery, full browser UI
   interactions, cloud LLM integrations, load/concurrency, backup recovery, TLS,
   and real infrastructure integration were not validated. Tests captured emails
   locally and used disposable data. Configure deployment-wide throttling for
   public authentication endpoints and review trust/proxy settings.
6. Research data/model usage rights must be checked before public redistribution.
   No project-wide license was selected on the owner's behalf. Full raw datasets
   and experimental models are intentionally excluded from the source upload.

## Publication and evidence

The GitHub snapshot starts a fresh history so ignored databases, large raw data,
scratch transcripts, and historical local state cannot travel in parent commits.
The original local `master` branch and its history are retained. Private
presentation/meeting files, credentials, keys, caches, generated vector indexes,
temporary outputs, and editor/agent settings are excluded.

A staged-file check tests for forbidden local-state files, files at least 95 MiB,
and common credential patterns. Pattern matching is a limited check, not a
guarantee that every possible secret has been identified.

Local detailed evidence is under ignored `tmp/review/`: `pytest.xml`, `pytest.log`,
`frontend-lint-final.json`, `npm-production-audit.json`, `npm-audit-fix.json`,
`python-audit-final.json`, and `live-rag.json`. These may contain test identities
and temporary test tokens, so raw logs are not uploaded. Reproduce the checks
using the README; CI produces a test-results artifact after upload.

Review consisted of source inspection, functional/regression testing, dependency
audits, and live local assistant checks. CodeRabbit was not run because a trusted
CLI installation was not found on PATH.
