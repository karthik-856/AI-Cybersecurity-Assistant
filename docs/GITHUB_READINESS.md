# Production and GitHub readiness — 16 November 2026

The repository is public and the production hardening pull request is merged.
The application passes the documented functional checks and is prepared for a
free demonstration deployment. Cloud publication and real-account validation
remain pending until the private hosting inputs are submitted.

## Verified evidence

[GitHub check run](https://github.com/karthik-856/AI-Cybersecurity-Assistant/actions/runs/43902839603)
for production hardening commit `8f58897` passed all three jobs:

- **190 backend tests passed** on Linux/Python 3.12 and PostgreSQL 16. There was
  one upstream Passlib deprecation warning about Python's `crypt` module; the
  runtime is pinned to Python 3.12. Local safety tests also pass with warnings
  treated as errors.
- **Seven browser tests passed**, covering all ten main routes, assistant answers
  and clearing history, settings saving, logout session invalidation, viewer
  restrictions, mobile navigation/layout, revoked-session redirects, and recovery
  when a page bundle is unavailable after a deployment.
- The Docker image builds and runs under a **512 MiB memory limit**. Its smoke
  checks exercise the actual built website, PostgreSQL initialization, login,
  detection, native TreeSHAP, PDF generation, and the offline knowledge assistant.
- Frontend TypeScript/production build and strict ESLint pass. The original
  **78 errors and seven warnings** were fixed without disabling rules.
- Both installed Python dependencies and all npm dependencies report **zero
  known security advisories** at review time. Audits do not establish absence
  of unknown vulnerabilities.
- An independent comparison against the original XGBClassifier wrapper matched
  **all 845 probabilities exactly** across the 65-row sample. Native inference
  preserves the trained early-stopping point. This is a functional regression
  check, not a new model accuracy or robustness evaluation.

## Changes

Authentication rejects plaintext password records, keeps existing bcrypt hash
compatibility, and revokes sessions on password changes, resets, and logout.
Public registration creates VIEWER accounts only; administrators assign roles.
Persistent atomic PostgreSQL budgets throttle public authentication operations.
Push destinations are restricted, and subscriptions cannot be reassigned to
another user. Database Center redacts session, OTP, and push secrets.

Production requires distinct generated signing/OTP secrets. The built website
and API share an origin, application deep links work, unknown API routes return
JSON 404s, and production security/no-cache headers are applied. Migrations and
role initialization run before server startup; there is no default owner password.

Chroma and its flagged dependencies were removed. Reviewed project knowledge
uses local hashed text vectors and an atomic SQLite index. Offline answers and
record operations need no paid AI API. Unknown questions return a fallback;
optional generated explanations require a separately configured model service.
The free deployment disables that optional service.

Frontend loopback URLs, stale state/effect handling, dead duplicate UI, and
verbose assistant metadata were removed or corrected. Viewers can access their
own Settings. Copy identifies dataset replay and recorded defense plans, and
fabricated reports, status claims, and prefilled containment/escalation assertions
were removed. Defense records do not enforce external firewall/device changes.

## Deployment limits and remaining validation

Use [the free deployment guide](FREE_DEPLOYMENT.md). A Neon Free project named
`zuka-soc` has been created in Frankfurt. The Render Free service has been
submitted and its first build is in progress.
No public website hostname is claimed as live until that service exists and its
readiness, login, and UI checks pass.

Free services sleep, have compute/storage/transfer limits, and provide no
always-on SOC availability commitment. A provider subdomain is included; a
custom `.com` domain is separate. Do not enable a paid upgrade automatically.

Real SMTP delivery and browser/OS push delivery have not been verified. Email
registration/recovery/two-factor actions are hidden or disabled without SMTP;
API email workflows are tested using captured messages. Backup restoration,
production load/concurrency, regional uptime, and real infrastructure integration
remain separate operational checks. Keep irreplaceable records backed up.

This is a research/demonstration SOC, not a production security appliance. The
65-row replay sample is not representative evidence of detection accuracy.
Research dataset/model usage terms require review before redistribution; no
project-wide license was chosen on the owner's behalf.

## Publication and collaboration

The published snapshot starts a fresh history; original local `master` and its
large research artifacts remain on the review computer. Credentials, account
databases, generated indexes, private meeting material, temporary evidence, and
raw/processed research datasets are excluded. Staged publication checks scan
for common credential patterns, forbidden local state, and oversized files;
pattern scanning is limited and cannot identify every possible secret.

[CONTRIBUTING.md](../CONTRIBUTING.md) explains teammate invitations, branches,
pull requests, and required checks. Source review, tests, audits, and browser
checks were used. CodeRabbit was unavailable because a trusted CLI installation
was not found. No claim is made that every possible operation, browser,
deployment, or attack scenario has been tested.
